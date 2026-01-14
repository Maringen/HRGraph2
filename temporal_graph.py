try:
    from graphiti_core import Graphiti
    from graphiti_core.driver.falkordb_driver import FalkorDriver

    GRAPHITI_AVAILABLE = True
except ImportError:
    GRAPHITI_AVAILABLE = False
    print("Warning: graphiti_core not found. Semantic search will be disabled.")

from falkordb import FalkorDB
from config import FALKORDB_HOST, FALKORDB_PORT, FALKORDB_DB, GRAPHITI_DB_URL
from models import Employee, Project
from datetime import datetime
from typing import Optional, Dict, Any
import random
from resume_parser import OpenResumeParser
import hashlib
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
        self.resume_parser = OpenResumeParser()

        # Try to connect to FalkorDB directly (Redis protocol)
        try:
            self.db = FalkorDB(host=FALKORDB_HOST, port=FALKORDB_PORT)
            self.graph_db = self.db.select_graph(FALKORDB_DB)
            print("✓ FalkorDB connection successful")
        except Exception as e:
            import traceback
            print(f"Warning: Could not connect to FalkorDB: {e}")
            traceback.print_exc()

        # Initialize Graphiti if available
        self.graph = None
        if GRAPHITI_AVAILABLE:
            try:
                driver = FalkorDriver(host=FALKORDB_HOST, port=FALKORDB_PORT)
                self.graph = Graphiti(graph_driver=driver)
                print("✓ Graphiti initialized successfully")
            except Exception as e:
                print(f"Warning: Could not initialize Graphiti: {e}")
                self.graph = None
        else:
            print("Using FalkorDB for graph data (Graphiti disabled)")

        if not self.graph_db and not self.graph:
            print("ERROR: No database connection available")

    async def add_episode(
        self,
        content: str,
        reference_time: datetime,
        name: str = "Ingested Document",
        source_description: str = "File ingestion",
    ):
        try:
            if not self.graph:
                raise ConnectionError("Graph not initialized - database unavailable")
            await self.graph.add_episode(
                name=name,
                episode_body=content,
                source_description=source_description,
                reference_time=reference_time,
            )
        except ConnectionError:
            raise
        except ValueError as e:
            raise ValueError(f"Invalid episode data: {e}")
        except Exception as e:
            raise ConnectionError(f"Error adding episode: {e}")

    def _fallback_search(self, query: str) -> str:
        if not self.graph_db:
            return "Graph not initialized - database unavailable"

        # Check if it looks like a Cypher query
        query_upper = query.strip().upper()
        is_cypher = (
            query_upper.startswith("MATCH")
            or query_upper.startswith("LOOKUP")
            or query_upper.startswith("CALL")
        )

        if is_cypher:
            # Execute Cypher query directly
            try:
                result = self.graph_db.query(query)
                if hasattr(result, "result_set"):
                    return f"Cypher Results ({len(result.result_set)} records): {str(result.result_set)}"
                return f"Cypher Results: {str(result)}"
            except Exception as e:
                return f"Cypher query error: {str(e)}"
        else:
            # Basic keyword search fallback
            # Search for nodes with name or label containing the query terms
            # Sanitize inputs to prevent injection in this basic fallback
            sanitized_query = re.sub(r"[^a-zA-Z0-9\s\-_]", "", query)

            if not sanitized_query:
                return "Please enter a valid search term."

            # Search across common property names
            cypher_query = (
                f"MATCH (n) "
                f"WHERE n.name CONTAINS '{sanitized_query}' "
                f"OR n.label CONTAINS '{sanitized_query}' "
                f"OR n.title CONTAINS '{sanitized_query}' "
                f"RETURN n.name, n.label, n.title, labels(n) LIMIT 10"
            )

            try:
                result = self.graph_db.query(cypher_query)
                if hasattr(result, "result_set") and result.result_set:
                    # Format results nicely
                    formatted = []
                    for r in result.result_set:
                        # r is [name, label, title, labels]
                        display_name = (
                            r[0] or r[1] or r[2] or (r[3][0] if r[3] else "Node")
                        )
                        node_type = r[3][0] if r[3] else "Node"
                        formatted.append(f"{display_name} ({node_type})")

                    return (
                        f"Found {len(formatted)} matches for '{query}':\n"
                        + "\n".join(formatted)
                    )
                else:
                    return (
                        f"No direct matches found for '{query}'.\n"
                        f"Since semantic search is currently unavailable, try a Cypher query like:\n"
                        f"MATCH (n:Employee) WHERE n.name CONTAINS '{sanitized_query}' RETURN n"
                    )
            except Exception as e:
                return f"Search failed: {str(e)}"

    async def query_hybrid(self, query: str) -> str:
        # Try Semantic Search (Graphiti) first if available
        if self.graph:
            try:
                results = await self.graph.search(query=query)
                return str(results)
            except Exception as e:
                print(
                    f"Warning: Semantic search failed, falling back to keyword search: {e}"
                )
                # Continue to fallback

        return self._fallback_search(query)

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

                label = props.get(
                    "name", props.get("title", labels[0] if labels else "Node")
                )

                # Debug CV nodes
                if "cv_" in node_id or node_id in [
                    "100",
                    "102",
                    "103",
                    "104",
                    "105",
                    "106",
                ]:
                    print(f"DEBUG: CV node {node_id} will be labeled as: '{label}'")
                
                # FIX APPLIED 2026-01-12: Removed duplicate nodes.append block here
            
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

    async def get_ontology(self) -> dict:
        """
        Extract the ontology from the HR graph for GraphRAG.
        Returns node types, relationship types, and their counts.
        """
        try:
            if not self.graph_db:
                return {"error": "Database not connected"}

            # Get node types and counts
            nodes_result = self.graph_db.query(
                "MATCH (n) RETURN labels(n) as labels, count(*) as count"
            )
            node_types = {}
            if hasattr(nodes_result, "result_set"):
                for record in nodes_result.result_set:
                    labels = record[0] if record[0] else ["Unknown"]
                    count = record[1]
                    # Use the primary label (first one)
                    primary_label = labels[0] if labels else "Unknown"
                    node_types[primary_label] = {
                        "count": count,
                        "labels": labels,
                        "description": self._get_node_description(primary_label),
                    }

            # Get relationship types and counts
            edges_result = self.graph_db.query(
                "MATCH ()-[r]->() RETURN type(r) as rel_type, count(*) as count"
            )
            relationship_types = {}
            if hasattr(edges_result, "result_set"):
                for record in edges_result.result_set:
                    rel_type = record[0] if record[0] else "UNKNOWN"
                    count = record[1]
                    relationship_types[rel_type] = {
                        "count": count,
                        "description": self._get_relationship_description(rel_type),
                        "direction": self._get_relationship_direction(rel_type),
                    }

            # Get sample entities for each type
            sample_entities = {}
            for node_type in node_types:
                # Use appropriate property for each node type
                if node_type == "Position":
                    prop = "title"
                else:
                    prop = "name"
                sample_result = self.graph_db.query(
                    f"MATCH (n:{node_type}) RETURN n.{prop} as name LIMIT 5"
                )
                if hasattr(sample_result, "result_set"):
                    samples = [r[0] for r in sample_result.result_set if r[0]]
                    if samples:
                        sample_entities[node_type] = samples

            return {
                "node_types": node_types,
                "relationship_types": relationship_types,
                "sample_entities": sample_entities,
                "total_nodes": sum(nt["count"] for nt in node_types.values()),
                "total_relationships": sum(
                    rt["count"] for rt in relationship_types.values()
                ),
            }
        except Exception as e:
            raise RuntimeError(f"Error extracting ontology: {e}")

    def _get_node_description(self, node_type: str) -> str:
        """Get human-readable description for node types."""
        descriptions = {
            "Employee": "Human resources - people working in the organization",
            "Department": "Organizational units like Engineering, Sales, Marketing",
            "Position": "Job titles and roles (CTO, Software Engineer, etc.)",
            "Skill": "Technical and soft skills (Python, Leadership, etc.)",
            "Project": "Initiatives and work products",
            "SkillGroup": "Categories of related skills",
            "UNKNOWN": "Unclassified entities",
        }
        return descriptions.get(node_type, f"Entity type: {node_type}")

    def _get_relationship_description(self, rel_type: str) -> str:
        """Get human-readable description for relationship types."""
        descriptions = {
            "BELONGS_TO": "Employee belongs to a department",
            "WORKS_IN": "Employee holds a position",
            "PROFICIENT_IN": "Employee has a skill",
            "REPORTS_TO": "Employee reports to a manager",
            "COLLABORATES_WITH": "Employees work together",
            "WORKS_ON": "Employee contributes to a project",
            "MANAGES": "Employee manages a department",
            "PART_OF": "Entity is part of a larger entity",
            "RELATED_TO": "Entities are connected",
        }
        return descriptions.get(rel_type, f"Relationship: {rel_type}")

    def _get_relationship_direction(self, rel_type: str) -> str:
        """Get the direction pattern for Cypher queries."""
        directions = {
            "BELONGS_TO": "(Employee)->[:BELONGS_TO]->(Department)",
            "WORKS_IN": "(Employee)->[:WORKS_IN]->(Position)",
            "PROFICIENT_IN": "(Employee)->[:PROFICIENT_IN]->(Skill)",
            "REPORTS_TO": "(Employee)->[:REPORTS_TO]->(Employee)",
            "COLLABORATES_WITH": "(Employee)<-[:COLLABORATES_WITH]->(Employee)",
            "WORKS_ON": "(Employee)->[:WORKS_ON]->(Project)",
            "MANAGES": "(Employee)->[:MANAGES]->(Department)",
            "PART_OF": "(Entity)->[:PART_OF]->(Entity)",
            "RELATED_TO": "(A)-[:RELATED_TO]->(B)",
        }
        return directions.get(rel_type, "(A)-[:]->(B)")

    async def query_with_ontology(self, query: str) -> str:
        """
        GraphRAG query that uses ontology context to enhance natural language queries.
        Extracts entities from the query, finds matching ontology patterns, and uses
        the graph structure to provide more accurate responses.
        """
        # First, get the ontology context
        ontology = await self.get_ontology()

        if "error" in ontology:
            # Fallback to regular query if ontology extraction fails
            return await self.query_hybrid(query)

        # Build context from ontology
        context_parts = []
        context_parts.append("=== HR Graph Ontology ===")
        context_parts.append(f"Total entities: {ontology['total_nodes']}")
        context_parts.append(f"Total relationships: {ontology['total_relationships']}")
        context_parts.append("")
        context_parts.append("Available entity types:")
        for node_type, info in ontology.get("node_types", {}).items():
            samples = ontology.get("sample_entities", {}).get(node_type, [])
            sample_str = f" (e.g., {', '.join(samples[:3])})" if samples else ""
            context_parts.append(
                f"  - {node_type}: {info['description']} [{info['count']}]{sample_str}"
            )

        context_parts.append("")
        context_parts.append("Available relationships:")
        for rel_type, info in ontology.get("relationship_types", {}).items():
            context_parts.append(
                f"  - {rel_type}: {info['description']} [{info['count']}]"
            )

        context_parts.append("")
        context_parts.append("=== Example Queries ===")
        context_parts.append(
            "• 'Who works in Engineering?' → MATCH (e:Employee)-[:BELONGS_TO]->(d:Department) WHERE d.name = 'Engineering'"
        )
        context_parts.append(
            "• 'Who is proficient in Python?' → MATCH (e:Employee)-[:PROFICIENT_IN]->(s:Skill) WHERE s.name = 'Python'"
        )
        context_parts.append(
            "• 'Who reports to the CTO?' → MATCH (e:Employee)-[:REPORTS_TO]->(m:Employee) WHERE m.position = 'CTO'"
        )

        ontology_context = "\n".join(context_parts)

        # Enhanced query with ontology context
        enhanced_query = f"""{ontology_context}

=== User Query ===
{query}

Please use the ontology above to understand the query and provide accurate results.
When responding, mention the entity types and relationship patterns used.
"""

        # Use semantic search with enhanced context
        if self.graph:
            try:
                # Use the enhanced query for semantic search
                results = await self.graph.search(query=enhanced_query)
                response = f"Based on the HR Knowledge Graph:\n\n{str(results)}"

                # Add helpful Cypher query suggestion
                suggested_cypher = self._suggest_cypher_query(query, ontology)
                if suggested_cypher:
                    response += f"\n\n💡 Equivalent Cypher query:\n```cypher\n{suggested_cypher}\n```"

                return response
            except Exception as e:
                print(f"Warning: GraphRAG search failed: {e}")

        # Use ontology to provide intelligent response without semantic search
        suggested_cypher = self._suggest_cypher_query(query, ontology)

        if suggested_cypher:
            # Execute the suggested Cypher query
            try:
                result = self.graph_db.query(suggested_cypher)
                if hasattr(result, "result_set") and result.result_set:
                    # Format results - simple and concise
                    names = []
                    for r in result.result_set:
                        name = r[0] if r[0] else "Unknown"
                        names.append(f"• {name}")

                    count = len(names)
                    return (
                        f"Found {count} result{'' if count == 1 else 's'}:\n"
                        + "\n".join(names)
                    )
                else:
                    return f"No results found."
            except Exception as e:
                return f"Error: {str(e)}"

        # No suggested Cypher query - provide helpful message
        return f"No results found for '{query}'.\n\nTry: 'Who works in Engineering?', 'Who is proficient in Python?', 'Who is the CTO?'"

    def _suggest_cypher_query(self, query: str, ontology: dict) -> str:
        """Suggest a Cypher query based on natural language query and ontology."""
        query_lower = query.lower()

        node_type = None
        rel_type = None
        target_keyword = None
        target_type = None

        # Detect entity types from query - check for specific positions first
        if any(word in query_lower for word in ["cfo", "chief financial officer"]):
            return "MATCH (e:Employee)-[:WORKS_IN]->(p:Position) WHERE p.title = 'CFO' RETURN e.name"
        elif any(word in query_lower for word in ["ceo", "chief executive officer"]):
            return "MATCH (e:Employee)-[:WORKS_IN]->(p:Position) WHERE p.title = 'CEO' RETURN e.name"
        elif any(word in query_lower for word in ["cto", "chief technology officer"]):
            return "MATCH (e:Employee)-[:WORKS_IN]->(p:Position) WHERE p.title = 'CTO' RETURN e.name"
        elif any(word in query_lower for word in ["director", "vp", "vice president"]):
            for pos in ["Director", "VP", "Vice President"]:
                if pos.lower() in query_lower:
                    return f"MATCH (e:Employee)-[:WORKS_IN]->(p:Position) WHERE p.title CONTAINS '{pos}' RETURN e.name"

        # Detect entity types from query
        if any(
            word in query_lower
            for word in ["employee", "staff", "worker", "who", "person"]
        ):
            node_type = "Employee"
        elif any(
            word in query_lower for word in ["department", "dept", "team", "unit"]
        ):
            node_type = "Department"
        elif any(word in query_lower for word in ["position", "role", "job", "title"]):
            node_type = "Position"
        elif any(
            word in query_lower for word in ["skill", "proficient", "expert", "knows"]
        ):
            node_type = "Skill"
            rel_type = "PROFICIENT_IN"
        elif any(word in query_lower for word in ["project", "work on"]):
            node_type = "Project"
            rel_type = "WORKS_ON"

        # Detect target entity - map keywords to actual entity names
        target_keyword_map = {
            # Departments
            "engineering": ("Department", "Engineering"),
            "sales": ("Department", "Sales"),
            "marketing": ("Department", "Marketing"),
            "finance": ("Department", "Finance"),
            "hr": ("Department", "Human Resources"),
            "human resources": ("Department", "Human Resources"),
            # Skills
            "python": ("Skill", "Python"),
            "javascript": ("Skill", "JavaScript"),
            "java": ("Skill", "Java"),
            "go": ("Skill", "Go"),
            "rust": ("Skill", "Rust"),
            "leadership": ("Skill", "Leadership"),
            "communication": ("Skill", "Communication"),
            "aws": ("Skill", "AWS"),
            "react": ("Skill", "React"),
            "node": ("Skill", "Node.js"),
            "node.js": ("Skill", "Node.js"),
            "docker": ("Skill", "Docker"),
            "kubernetes": ("Skill", "Kubernetes"),
            "sql": ("Skill", "SQL"),
            "postgresql": ("Skill", "PostgreSQL"),
            "mongodb": ("Skill", "MongoDB"),
            "redis": ("Skill", "Redis"),
            "machine learning": ("Skill", "Machine Learning"),
            "tensorflow": ("Skill", "TensorFlow"),
            "devops": ("Skill", "DevOps"),
            "cybersecurity": ("Skill", "Cybersecurity"),
            # Positions
            "cto": ("Position", "CTO"),
            "cfo": ("Position", "CFO"),
            "ceo": ("Position", "CEO"),
            "engineer": ("Position", "Engineer"),
            "manager": ("Position", "Manager"),
            "director": ("Position", "Director"),
        }

        for word, (type_name, entity_name) in target_keyword_map.items():
            if word in query_lower:
                target_keyword = entity_name
                target_type = type_name
                break

        # Detect relationships based on keywords
        if (
            "proficient" in query_lower
            or "expert" in query_lower
            or "knows" in query_lower
        ):
            rel_type = "PROFICIENT_IN"
        elif (
            "belong" in query_lower
            or " in " in query_lower
            or query_lower.endswith(" in")
        ):
            rel_type = "BELONGS_TO"
        elif (
            "report" in query_lower
            or "manager" in query_lower
            or "supervis" in query_lower
        ):
            rel_type = "REPORTS_TO"
        elif "work" in query_lower and (
            "position" in query_lower or "role" in query_lower
        ):
            rel_type = "WORKS_IN"
        elif "collaborat" in query_lower or "work with" in query_lower:
            rel_type = "COLLABORATES_WITH"
        elif "manage" in query_lower or "lead" in query_lower:
            rel_type = "MANAGES"

        # Build Cypher query based on detected patterns - return names only
        if target_keyword and target_type:
            if target_type == "Skill":
                return f"MATCH (e:Employee)-[:PROFICIENT_IN]->(s:Skill) WHERE s.name CONTAINS '{target_keyword}' RETURN e.name"
            elif target_type == "Department":
                return f"MATCH (e:Employee)-[:BELONGS_TO]->(d:Department) WHERE d.name = '{target_keyword}' RETURN e.name"
            elif target_type == "Position":
                return f"MATCH (e:Employee)-[:WORKS_IN]->(p:Position) WHERE p.title = '{target_keyword}' RETURN e.name"
        elif node_type and rel_type:
            if rel_type == "PROFICIENT_IN":
                return "MATCH (e:Employee)-[:PROFICIENT_IN]->(s:Skill) RETURN e.name LIMIT 20"
            elif rel_type == "BELONGS_TO":
                return "MATCH (e:Employee)-[:BELONGS_TO]->(d:Department) RETURN e.name LIMIT 20"
            elif rel_type == "REPORTS_TO":
                return "MATCH (e:Employee)-[:REPORTS_TO]->(m:Employee) RETURN e.name, m.name LIMIT 20"
            elif rel_type == "WORKS_IN":
                return "MATCH (e:Employee)-[:WORKS_IN]->(p:Position) RETURN e.name LIMIT 20"
            elif rel_type == "COLLABORATES_WITH":
                return "MATCH (e:Employee)-[:COLLABORATES_WITH]->(e2:Employee) RETURN e.name, e2.name LIMIT 20"
        elif node_type:
            if node_type == "Employee":
                return "MATCH (e:Employee) RETURN e.name LIMIT 20"
            elif node_type == "Department":
                return "MATCH (d:Department) RETURN d.name LIMIT 20"
            elif node_type == "Position":
                return "MATCH (p:Position) RETURN p.title LIMIT 20"
            elif node_type == "Skill":
                return "MATCH (s:Skill) RETURN s.name LIMIT 20"

        return ""

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
                            # Use OpenResumeParser for high-quality structured extraction
                            parsed_data = self.resume_parser.parse(file_path)
                            reference_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                            await self._insert_parsed_cv_data(parsed_data, filename, reference_time)
                            processed_files += 1
                            continue # Successfully processed with OpenResume parser
                        else:
                            text = self.extract_text_from_md(file_path)

                        cleaned_text = self.clean_text(text)
                        reference_time = datetime.fromtimestamp(
                            os.path.getmtime(file_path)
                        )

                        # Try LLM-based ingestion for non-PDFs or general episodes
                        await self.add_episode(cleaned_text, reference_time)

                        processed_files += 1

                    except Exception as file_error:
                        print(f"Error processing file {filename}: {file_error}")
                        continue

            return processed_files
        except Exception as e:
            raise RuntimeError(f"Error during ingestion: {e}")

    async def _insert_parsed_cv_data(
        self, parsed_data: Dict[str, Any], filename: str, reference_time: datetime
    ):
        """Insert structured CV data from OpenResumeParser into FalkorDB"""
        try:
            if not self.db or not self.graph_db:
                raise ConnectionError("FalkorDB not available")

            profile = parsed_data.get("profile", {})
            candidate_name = profile.get("name") or filename.split('.')[0].replace('_', ' ').strip()
            
            if candidate_name.lower() in ["sample employee", "test document"]:
                return

            email = profile.get("email", "")
            phone = profile.get("phone", "")
            
            # Create a unique but deterministic node ID
            node_id = f"cv_{hashlib.md5(candidate_name.encode()).hexdigest()[:8]}"
            department = "Engineering" # Default
            
            # 1. Insert Employee node
            query = f"""
            MERGE (e:Employee {{id: '{node_id}'}})
            SET e.name = '{candidate_name.replace("'", "\\'")}',
                e.email = '{email.replace("'", "\\'")}',
                e.phone = '{phone.replace("'", "\\'")}',
                e.position = 'Candidate',
                e.department = '{department}',
                e.source_file = '{filename}'
            MERGE (d:Department {{label: '{department}'}})
            MERGE (e)-[:BELONGS_TO]->(d)
            """
            self.graph_db.query(query)

            # 2. Insert Skills and Relationships
            skills = parsed_data.get("skills", [])
            for skill in skills:
                if len(skill) > 50: continue # Skip long descriptions
                skill_id = f"skill_{hashlib.md5(skill.lower().encode()).hexdigest()[:8]}"
                skill_query = f"""
                MATCH (e:Employee {{id: '{node_id}'}})
                MERGE (s:Skill {{name: '{skill.replace("'", "\\'")}'}})
                ON CREATE SET s.id = '{skill_id}', s.category = 'Extracted'
                MERGE (e)-[:HAS_SKILL {{proficiency: 'Intermediate'}}]->(s)
                """
                self.graph_db.query(skill_query)

            print(f"✓ Inserted parsed CV data for {candidate_name} with {len(skills)} skills")

        except Exception as e:
            print(f"Warning: Could not insert parsed CV data: {e}")
