from graphiti_core import Graphiti
from graphiti_core.driver.falkordb_driver import FalkorDriver
from falkordb import FalkorDB
from config import FALKORDB_HOST, FALKORDB_PORT, FALKORDB_DB, GRAPHITI_DB_URL
from models import Employee, Project
from datetime import datetime
from typing import Optional
import random
import os
import sys
import platform
import PyPDF2
import re
import signal
from contextlib import contextmanager


PDF_MAX_FILE_SIZE = 50 * 1024 * 1024
PDF_MAX_PAGES = 1000
PDF_MAX_TEXT_SIZE = 10000000
PDF_PAGE_MAX_TEXT = 100000
PDF_PROCESSING_TIMEOUT = 30


class HRTemporalGraph:
    def __init__(self):
        self.graph = None
        self.db = None
        self.graph_db = None

        # Try to connect to FalkorDB directly (Redis protocol)
        try:
            self.db = FalkorDB(host=FALKORDB_HOST, port=FALKORDB_PORT)
            self.graph_db = self.db.select_graph(FALKORDB_DB)
            print("✓ FalkorDB connection successful")
        except Exception as e:
            print(f"Warning: Could not connect to FalkorDB: {e}")

        # Try to connect to Graphiti (Bolt protocol - may fail with FalkorDB)
        try:
            self.graph = Graphiti(uri=GRAPHITI_DB_URL)
            print("✓ Graphiti connection successful")
        except Exception as e:
            print(f"Warning: Could not initialize Graphiti (Bolt protocol): {e}")
            print("  Graph visualization will use FalkorDB directly")

        if not self.graph_db and not self.graph:
            print("ERROR: No database connection available")

    async def add_episode(self, content: str, reference_time: datetime):
        try:
            if not self.graph:
                raise ConnectionError("Graph not initialized - database unavailable")
            await self.graph.add_episode(content, reference_time)
        except ConnectionError:
            raise
        except ValueError as e:
            raise ValueError(f"Invalid episode data: {e}")
        except Exception as e:
            raise ConnectionError(f"Error adding episode: {e}")

    async def query_hybrid(self, query: str) -> str:
        try:
            if not self.graph:
                return "Graph not initialized - database unavailable"
            results = await self.graph.search(query=query)
            return str(results)
        except Exception as e:
            raise RuntimeError(f"Error in hybrid search: {e}")

    async def get_employee_history(self, employee_name: str) -> str:
        try:
            if not self.graph:
                return "Graph not initialized - database unavailable"
            # Use Graphiti's temporal logic to get history
            results = await self.graph.search(query=f"employee {employee_name}")
            # Assuming results have valid_at and expired_at
            history = []
            if hasattr(results, "__iter__"):
                for result in results:
                    if hasattr(result, "get"):
                        history.append(
                            f"At {result.get('valid_at', 'unknown')}: {result}"
                        )
                    else:
                        history.append(f"At unknown: {result}")
            else:
                history.append(f"Results: {results}")
            return "\n".join(history)
        except Exception as e:
            raise RuntimeError(f"Error getting employee history: {e}")

    async def get_graph_data(self):
        try:
            # Try FalkorDB direct connection first
            if self.graph_db:
                nodes_result = self.graph_db.query(
                    "MATCH (n) RETURN id(n) as id, labels(n) as labels, properties(n) as props"
                )
            elif self.graph:
                # Fallback to Graphiti
                nodes_result = []
            else:
                return {"nodes": [], "edges": []}

            nodes = []
            # FalkorDB QueryResult has result_set attribute
            if hasattr(nodes_result, "result_set"):
                nodes_records = nodes_result.result_set
            elif hasattr(nodes_result, "__iter__"):
                nodes_records = list(nodes_result)
            else:
                nodes_records = []

            for record in nodes_records:
                # record format: [id, labels, props]
                node_id = str(record[0])
                labels = record[1] if len(record) > 1 else []
                props = record[2] if len(record) > 2 else {}
                label = props.get(
                    "name", props.get("title", labels[0] if labels else "Node")
                )
                x = random.uniform(-100, 100)
                y = random.uniform(-100, 100)
                size = 1
                nodes.append(
                    {
                        "id": node_id,
                        "label": label,
                        "x": x,
                        "y": y,
                        "size": size,
                        "labels": labels,
                    }
                )

            # Get edges - only if we have FalkorDB connection
            edges = []
            if self.graph_db:
                edges_result = self.graph_db.query(
                    "MATCH (a)-[r]->(b) RETURN id(r) as id, id(a) as source, id(b) as target, type(r) as type"
                )
                # FalkorDB QueryResult has result_set attribute
                if hasattr(edges_result, "result_set"):
                    edges_records = edges_result.result_set
                elif hasattr(edges_result, "__iter__"):
                    edges_records = list(edges_result)
                else:
                    edges_records = []

                for record in edges_records:
                    # record format: [id, source, target, type]
                    edge_id = str(record[0])
                    source = str(record[1])
                    target = str(record[2])
                    label = record[3] if len(record) > 3 else ""
                    edges.append(
                        {
                            "id": edge_id,
                            "source": source,
                            "target": target,
                            "label": label,
                        }
                    )
            return {"nodes": nodes, "edges": edges}
        except Exception as e:
            raise RuntimeError(f"Error getting graph data: {e}")

    @contextmanager
    def timeout_handler(self, duration):
        if platform.system() == "Windows":
            import asyncio

            try:
                yield
                return
            except asyncio.TimeoutError:
                raise TimeoutError(f"PDF processing timed out after {duration} seconds")

        def timeout_handler(signum, frame):
            raise TimeoutError(f"PDF processing timed out after {duration} seconds")

        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(duration)
        try:
            yield
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)

    def extract_text_from_pdf(self, file_path: str) -> str:
        file_size = os.path.getsize(file_path)
        if file_size > PDF_MAX_FILE_SIZE:
            raise ValueError(f"PDF file too large: {file_size // (1024 * 1024)}MB")

        try:
            with self.timeout_handler(PDF_PROCESSING_TIMEOUT):
                with open(file_path, "rb") as file:
                    reader = PyPDF2.PdfReader(file)

                    if reader.is_encrypted:
                        raise ValueError("Encrypted PDFs are not supported")

                    if len(reader.pages) > PDF_MAX_PAGES:
                        raise ValueError("PDF has too many pages")

                    text = ""
                    for page_num, page in enumerate(reader.pages):
                        if page_num >= PDF_MAX_PAGES:
                            break
                        try:
                            page_text = page.extract_text()
                            if page_text and len(page_text) < PDF_PAGE_MAX_TEXT:
                                text += page_text + "\n"
                        except Exception as page_error:
                            print(
                                f"Warning: Could not extract text from page {page_num}: {page_error}"
                            )
                            continue

                    if len(text) > PDF_MAX_TEXT_SIZE:
                        raise ValueError("Extracted text too large")

                    return text
        except TimeoutError:
            raise ValueError(
                "PDF processing timed out - file may be corrupted or too complex"
            )

    def extract_text_from_md(self, file_path: str) -> str:
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()

    def clean_text(self, text: str) -> str:
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    async def ingest_documents(self, vault_path: str):
        try:
            if not os.path.exists(vault_path):
                raise FileNotFoundError(f"Vault path {vault_path} not found")

            processed_files = 0
            for filename in os.listdir(vault_path):
                if filename.endswith(".pdf") or filename.endswith(".md"):
                    file_path = os.path.join(vault_path, filename)

                    try:
                        if filename.endswith(".pdf"):
                            text = self.extract_text_from_pdf(file_path)
                        else:
                            text = self.extract_text_from_md(file_path)

                        cleaned_text = self.clean_text(text)
                        reference_time = datetime.fromtimestamp(
                            os.path.getmtime(file_path)
                        )

                        await self.add_episode(cleaned_text, reference_time)
                        processed_files += 1

                    except Exception as file_error:
                        print(f"Error processing file {filename}: {file_error}")
                        continue

            return processed_files
        except Exception as e:
            raise RuntimeError(f"Error during ingestion: {e}")
