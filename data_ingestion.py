import asyncio
import os
import re
from pathlib import Path
from datetime import datetime
from cocoindex import Flow, Source, Transform, Sink
from temporal_graph import HRTemporalGraph
import PyPDF2
import signal
from contextlib import contextmanager
from typing import Dict, Any


@contextmanager
def timeout_handler(duration):
    def timeout_handler(signum, frame):
        raise TimeoutError(f"PDF processing timed out after {duration} seconds")

    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(duration)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


def extract_text_from_pdf(file_path: str) -> str:
    file_size = os.path.getsize(file_path)
    if file_size > 50 * 1024 * 1024:
        raise ValueError(f"PDF file too large: {file_size // (1024 * 1024)}MB")

    try:
        with timeout_handler(30):
            with open(file_path, "rb") as file:
                reader = PyPDF2.PdfReader(file)

                if reader.is_encrypted:
                    raise ValueError("Encrypted PDFs are not supported")

                if len(reader.pages) > 1000:
                    raise ValueError("PDF has too many pages")

                text = ""
                for page_num, page in enumerate(reader.pages):
                    if page_num >= 1000:
                        break
                    try:
                        page_text = page.extract_text()
                        if page_text and len(page_text) < 100000:
                            text += page_text + "\n"
                    except Exception as page_error:
                        print(
                            f"Warning: Could not extract text from page {page_num}: {page_error}"
                        )
                        continue

                if len(text) > 10000000:
                    raise ValueError("Extracted text too large")

                return text
    except TimeoutError:
        raise ValueError(
            "PDF processing timed out - file may be corrupted or too complex"
        )


def extract_text_from_md(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_reference_time(metadata: Dict[str, Any]) -> datetime:
    # Extract from file metadata or use current time
    mtime = metadata.get("mtime")
    if mtime:
        return datetime.fromtimestamp(mtime)
    return datetime.now()


class GraphitiSink(Sink):
    def __init__(self):
        self.graph = None

    async def initialize(self):
        self.graph = HRTemporalGraph()

    async def process(self, data: Dict[str, Any]):
        content = data["cleaned_text"]
        reference_time = data["reference_time"]
        await self.graph.add_episode(content, reference_time)


# Define CocoIndex Flow
flow = Flow(
    name="hr_data_ingestion",
    sources=[
        Source(
            type="file_watcher",
            config={
                "path": "./hr_vault",
                "patterns": ["*.pdf", "*.md"],
                "incremental": True,
            },
        )
    ],
    transforms=[
        Transform(
            name="extract_text",
            func=lambda data: {
                **data,
                "text": extract_text_from_pdf(data["path"])
                if data["path"].endswith(".pdf")
                else extract_text_from_md(data["path"]),
            },
        ),
        Transform(
            name="clean_text",
            func=lambda data: {**data, "cleaned_text": clean_text(data["text"])},
        ),
        Transform(
            name="add_reference_time",
            func=lambda data: {
                **data,
                "reference_time": extract_reference_time(data.get("metadata", {})),
            },
        ),
    ],
    sink=GraphitiSink(),
)


async def run_ingestion():
    try:
        await flow.run()
    except FileNotFoundError:
        print("Error: hr_vault directory not found.")
    except ConnectionRefusedError:
        print("Error: Connection to database refused.")
    except Exception as e:
        print(f"Ingestion error: {e}")


if __name__ == "__main__":
    asyncio.run(run_ingestion())
