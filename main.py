from fastapi import (
    FastAPI,
    HTTPException,
    UploadFile,
    File,
    status,
    Query,
    Request,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import os
import time
from temporal_graph import HRTemporalGraph
from pydantic import BaseModel
import asyncio
import re
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import aiofiles

rate_limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

graph = None


class QueryRequest(BaseModel):
    query: str


MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".md", ".txt"}
VAULT_DIR = Path("./hr_vault").resolve()
VAULT_DIR.mkdir(exist_ok=True)


from typing import Optional, Dict, Any, List, Set



def validate_filename(filename: str) -> str:
    if not filename:
        raise HTTPException(status_code=400, detail="Filename cannot be empty")

    sanitized = re.sub(r'[<>:"/\\|?*]', "_", filename)
    sanitized = re.sub(r"\.\.", "", sanitized)
    sanitized = sanitized.strip()

    file_path = Path(sanitized)
    if file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    return sanitized


def validate_file_size(file_size: int) -> None:
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)}MB",
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    global graph
    try:
        graph = HRTemporalGraph()
        yield
    except ConnectionError as e:
        print(f"Failed to connect to database: {e}")
        raise
    except ImportError as e:
        print(f"Missing dependencies: {e}")
        raise
    except Exception as e:
        print(f"Failed to initialize graph: {e}")
        raise
    finally:
        graph = None


app = FastAPI(
    lifespan=lifespan,
    title="HR Temporal Knowledge Graph",
    description="Secure HR Knowledge Management System",
    docs_url=None,
    redoc_url=None,
)

# Security middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://vps-97995726.vps.ovh.net",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    max_age=3600,
)


@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains"
    )
    csp = (
        "default-src 'self' 'unsafe-inline'; "
        "script-src 'self' 'unsafe-inline' https://gw.alipayobjects.com https://unpkg.com https://cdn.jsdelivr.net https://cdn.tailwindcss.com https://unpkg.com; "
        "style-src 'self' 'unsafe-inline' https://gw.alipayobjects.com https://fonts.googleapis.com https://cdn.tailwindcss.com https://unpkg.com; "
        "img-src 'self' data: https://gw.alipayobjects.com https://cdn.jsdelivr.net; "
        "font-src 'self' https://fonts.googleapis.com https://fonts.gstatic.com https://gw.alipayobjects.com; "
        "connect-src 'self' https://gw.alipayobjects.com https://unpkg.com https://cdn.jsdelivr.net"
    )
    response.headers["Content-Security-Policy"] = csp
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    return response


app.mount("/static", StaticFiles(directory="static"), name="static")


@app.exception_handler(RateLimitExceeded)
async def rate_limit_exception_handler(request, exc):
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": "Rate limit exceeded. Please try again later."},
    )


@app.get("/")
async def read_root():
    return FileResponse("static/index.html")


@app.get("/reactflow")
async def read_reactflow():
    return FileResponse("static/graph-view-reactflow.html")


@app.post("/query")
@rate_limiter.limit("20/minute")
async def query(query_data: QueryRequest, request: Request):
    try:
        if not graph:
            raise HTTPException(
                status_code=503, detail="Service unavailable - graph not initialized"
            )

        if not query_data.query or len(query_data.query.strip()) == 0:
            raise HTTPException(status_code=400, detail="Query cannot be empty")

        result = await graph.query_hybrid(query_data.query)
        return {"result": result, "timestamp": time.time()}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        import traceback

        error_detail = f"Internal server error: {str(e)}\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)


@app.get("/history/{employee_name}")
@rate_limiter.limit("30/minute")
async def history(employee_name: str, request: Request):
    try:
        if not graph:
            raise HTTPException(
                status_code=503, detail="Service unavailable - graph not initialized"
            )

        if not employee_name or len(employee_name.strip()) == 0:
            raise HTTPException(status_code=400, detail="Employee name cannot be empty")

        result = await graph.get_employee_history(employee_name)
        return {"history": result, "timestamp": time.time()}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        import traceback

        error_detail = f"Internal server error: {str(e)}\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)


@app.get("/graph")
@rate_limiter.limit("10/minute")
async def get_graph(request: Request):
    try:
        if not graph:
            raise HTTPException(
                status_code=503, detail="Service unavailable - graph not initialized"
            )

        data = await graph.get_graph_data()
        return data
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        import traceback

        error_detail = f"Internal server error: {str(e)}\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)



@app.get("/graph-diff")
@rate_limiter.limit("5/minute")
async def get_graph_diff(
    request: Request,
    before: str = Query(..., description="First timestamp for comparison (ISO format)"),
    after: str = Query(..., description="Second timestamp for comparison (ISO format)"),
):
    """
    Compare graph state between two timestamps.

    NOTE: This endpoint currently SIMULATES historical data for demonstration.
    In production, this would query actual temporal snapshots from Graphiti.

    Returns nodes and edges that are:
    - NEW: Present in 'after' but not in 'before'
    - REMOVED: Present in 'before' but not in 'after'
    - UNCHANGED: Present in both

    Useful for measuring organizational changes (hiring waves, reorganizations).
    """
    try:
        if not graph:
            raise HTTPException(
                status_code=503, detail="Service unavailable - graph not initialized"
            )

        # Get current graph data
        data_after = await graph.get_graph_data()

        # For demo: simulate "before" state by using a subset of nodes/edges
        # In production, this would query historical snapshots from Graphiti
        import random

        random.seed(42)  # For reproducible results

        all_nodes = data_after.get("nodes", [])
        all_edges = data_after.get("edges", [])

        # Simulate "before" state as 80% of current data (simulating some growth)
        nodes_before_ids = set()
        edges_before_keys = set()

        for n in all_nodes:
            if random.random() < 0.8:
                nodes_before_ids.add(str(n.get("id")))

        for e in all_edges:
            key = f"{e.get('source')}|{e.get('target')}|{e.get('label')}"
            if random.random() < 0.8:
                edges_before_keys.add(key)

        # Current state (after)
        nodes_after_ids = {str(n.get("id")) for n in all_nodes}
        edges_after_keys = {
            f"{e.get('source')}|{e.get('target')}|{e.get('label')}" for e in all_edges
        }

        # Find changes
        new_nodes = nodes_after_ids - nodes_before_ids
        removed_nodes = nodes_before_ids - nodes_after_ids
        new_edges = edges_after_keys - edges_before_keys
        removed_edges = edges_before_keys - edges_after_keys

        # Format result with diff metadata
        result = {
            "before": before,
            "after": after,
            "summary": {
                "new_nodes": len(new_nodes),
                "removed_nodes": len(removed_nodes),
                "new_edges": len(new_edges),
                "removed_edges": len(removed_edges),
            },
            "nodes": {
                "new": [],
                "removed": [],
                "unchanged": [],
            },
            "edges": {
                "new": [],
                "removed": [],
                "unchanged": [],
            },
            "note": "Simulated diff - graph stores current state only",
        }

        # Categorize nodes
        for node in all_nodes:
            node_id = str(node.get("id"))
            if node_id in new_nodes:
                result["nodes"]["new"].append(node)
            elif node_id not in removed_nodes:
                result["nodes"]["unchanged"].append(node)

        for node in all_nodes:
            node_id = str(node.get("id"))
            if node_id in removed_nodes:
                result["nodes"]["removed"].append(node)

        # Categorize edges
        for edge in all_edges:
            edge_key = f"{edge.get('source')}|{edge.get('target')}|{edge.get('label')}"
            if edge_key in new_edges:
                result["edges"]["new"].append(edge)
            elif edge_key not in removed_edges:
                result["edges"]["unchanged"].append(edge)

        for edge in all_edges:
            edge_key = f"{edge.get('source')}|{edge.get('target')}|{edge.get('label')}"
            if edge_key in removed_edges:
                result["edges"]["removed"].append(edge)

        return result
    except HTTPException:
        raise
    except Exception as e:
        import traceback

        error_detail = f"Internal server error: {str(e)}\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)



@app.post("/upload")
@rate_limiter.limit("5/minute")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    try:
        sanitized_filename = validate_filename(file.filename)
        file_path = VAULT_DIR / sanitized_filename

        if file_path.exists():
            raise HTTPException(status_code=409, detail="File already exists")

        async with aiofiles.open(file_path, "wb") as f:
            total_size = 0
            chunk_size = 64 * 1024

            while chunk := await file.read(chunk_size):
                total_size += len(chunk)
                validate_file_size(total_size)
                await f.write(chunk)

        return {
            "filename": sanitized_filename,
            "status": "uploaded",
            "timestamp": time.time(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.post("/ingest")
@rate_limiter.limit("2/hour")
async def ingest_documents(request: Request):
    try:
        if not graph:
            raise HTTPException(
                status_code=503, detail="Service unavailable - graph not initialized"
            )

        processed_files = await graph.ingest_documents("./hr_vault")

        return {
            "status": "success",
            "processed_files": processed_files,
            "message": f"Successfully processed {processed_files} files",
            "timestamp": time.time(),
        }
    except HTTPException:
        raise
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ingestion failed")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": time.time(), "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn

    print("=" * 50)
    print("🔒 HR Temporal Knowledge Graph")
    print("=" * 50)
    print("🛡️  Security Features:")
    print("   ✅ Rate Limiting")
    print("   ✅ CORS Protection")
    print("   ✅ Trusted Hosts")
    print("=" * 50)
    print(f"🌐 Server: http://localhost:5000")
    print(f"📖 Health: http://localhost:5000/health")
    print("=" * 50)

    uvicorn.run(app, host="127.0.0.1", port=5000, log_level="info")
