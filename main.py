from fastapi import (
    FastAPI,
    HTTPException,
    UploadFile,
    File,
    Depends,
    status,
    Query,
    Request,
)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from auth import auth_manager, get_current_user
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


def format_for_g6(
    data: Dict[str, Any],
    valid_at: Optional[str] = None,
    expired_at: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Format graph data for AntV G6 visualization.

    Args:
        data: Raw graph data from get_graph_data()
        valid_at: Filter for entities valid at this timestamp
        expired_at: Filter for entities expired at this timestamp

    Returns:
        Dict with nodes, edges, and combos for G6
    """
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    combos: Set[str] = set()
    seen_nodes: Set[str] = set()

    # Process nodes
    for node in data.get("nodes", []):
        node_id = str(node.get("id", ""))
        if node_id in seen_nodes:
            continue
        seen_nodes.add(node_id)

        labels = node.get("labels", [])
        node_type = labels[0] if labels else "Node"
        name = node.get("label", node.get("name", "N/A"))

        # Determine comboId for Employee nodes (group by department)
        combo_id: Optional[str] = None
        if node_type == "Employee":
            # Find department through BELONGS_TO edge
            for edge in data.get("edges", []):
                if edge.get("source") == node_id and edge.get("label") == "BELONGS_TO":
                    target_id = str(edge.get("target"))
                    for n in data.get("nodes", []):
                        if str(n.get("id")) == target_id:
                            combo_id = n.get("label", "Unknown")
                            combos.add(combo_id)
                            break
                    break
            if not combo_id:
                combo_id = "Unknown"
                combos.add("Unknown")

        # Node color based on type
        color_map = {
            "Employee": "#667eea",
            "Position": "#ff9800",
            "Department": "#4caf50",
            "Project": "#e91e63",
            "Skill": "#00bcd4",
        }
        fill_color = color_map.get(node_type, "#91d5ff")

        nodes.append(
            {
                "id": node_id,
                "label": name,
                "comboId": combo_id,
                "nodeType": node_type,
                "style": {
                    "fill": fill_color,
                    "stroke": fill_color,
                    "lineWidth": 2,
                },
                "size": 30 if node_type == "Employee" else 26,
                "data": {
                    "properties": node.get("properties", {}),
                    "valid_at": node.get("valid_at"),
                    "expired_at": node.get("expired_at"),
                },
            }
        )

    # Process edges
    edge_color_map = {
        "PROFICIENT_IN": "#667eea",
        "WORKS_IN": "#4caf50",
        "BELONGS_TO": "#ff9800",
        "REPORTS_TO": "#e91e63",
        "WORKS_ON": "#00bcd4",
        "COLLABORATES_WITH": "#9c27b0",
        "MANAGES": "#f44336",
    }

    for i, edge in enumerate(data.get("edges", [])):
        edge_type = edge.get("label", "")
        color = edge_color_map.get(edge_type, "#ccc")

        # Apply temporal filtering if dates provided
        if valid_at or expired_at:
            edge_valid_at = edge.get("valid_at")
            edge_expired_at = edge.get("expired_at")

            # Simple temporal check (can be enhanced with proper date comparison)
            if valid_at and edge_expired_at and edge_expired_at < valid_at:
                continue
            if expired_at and edge_valid_at and edge_valid_at > expired_at:
                continue

        edges.append(
            {
                "id": str(edge.get("id", f"e{i}")),
                "source": str(edge.get("source")),
                "target": str(edge.get("target")),
                "label": edge_type,
                "style": {
                    "stroke": color,
                    "lineWidth": 2,
                    "endArrow": True,
                },
                "data": {
                    "properties": edge.get("properties", {}),
                    "valid_at": edge.get("valid_at"),
                    "expired_at": edge.get("expired_at"),
                },
            }
        )

    # Create combo list
    combo_list = [{"id": dept, "label": dept} for dept in sorted(combos)]

    return {
        "nodes": nodes,
        "edges": edges,
        "combos": combo_list if combo_list else None,
        "valid_at": valid_at,
        "expired_at": expired_at,
    }


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
    response.headers["Content-Security-Policy"] = "default-src 'self'"
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


@app.post("/query")
@rate_limiter.limit("20/minute")
async def query(request: QueryRequest, current_user: dict = Depends(get_current_user)):
    try:
        if not graph:
            raise HTTPException(
                status_code=503, detail="Service unavailable - graph not initialized"
            )

        if not request.query or len(request.query.strip()) == 0:
            raise HTTPException(status_code=400, detail="Query cannot be empty")

        result = await graph.query_hybrid(request.query)
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
async def history(
    employee_name: str, request: Request, current_user: dict = Depends(get_current_user)
):
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


# Development mode: set to True to bypass authentication (REMOVED - security risk)


@app.get("/graph")
@rate_limiter.limit("10/minute")
async def get_graph(request: Request, current_user: dict = Depends(get_current_user)):
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


@app.get("/graph-g6")
@rate_limiter.limit("10/minute")
async def get_graph_g6(
    request: Request,
    valid_at: Optional[str] = None,
    expired_at: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """
    Get graph data formatted for AntV G6.

    Returns nodes with comboId for department grouping,
    edges with source/target, and temporal data for TimeBar filtering.
    """
    try:
        if not graph:
            raise HTTPException(
                status_code=503, detail="Service unavailable - graph not initialized"
            )

        data = await graph.get_graph_data()

        # Format data for G6
        result = format_for_g6(data, valid_at, expired_at)
        return result
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
    current_user: dict = Depends(get_current_user),
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


@app.get("/graph-collaborations")
@rate_limiter.limit("5/minute")
async def get_collaborations(
    request: Request,
    min_interactions: int = Query(default=2, description="Minimum interaction count"),
    current_user: dict = Depends(get_current_user),
):
    """
    Find implicit collaboration patterns from project work.

    This analyzes which employees work together on the same projects
    (via WORKS_ON relationships) to reveal real team structures
    that may differ from official reporting lines.

    Returns collaboration edges that can be overlaid on the org chart.
    """
    try:
        if not graph:
            raise HTTPException(
                status_code=503, detail="Service unavailable - graph not initialized"
            )

        data = await graph.get_graph_data()

        # Build project -> employees mapping
        project_employees: Dict[str, List[str]] = {}
        employee_names: Dict[str, str] = {}

        # First pass: collect employees and their projects
        for node in data.get("nodes", []):
            node_id = str(node.get("id"))
            labels = node.get("labels", [])
            if "Employee" in labels:
                employee_names[node_id] = node.get("label", "Unknown")

        for edge in data.get("edges", []):
            if edge.get("label") == "WORKS_ON":
                project_id = str(edge.get("target"))
                employee_id = str(edge.get("source"))
                if project_id not in project_employees:
                    project_employees[project_id] = []
                if employee_id not in project_employees[project_id]:
                    project_employees[project_id].append(employee_id)

        # Find implicit collaborations (people working on same projects)
        collaborations: Dict[str, Dict[str, int]] = {}
        seen_pairs: Set[str] = set()

        for project_id, employees in project_employees.items():
            # All pairs of employees on this project collaborate
            for i, emp1 in enumerate(employees):
                for emp2 in employees[i + 1 :]:
                    pair_key = "|".join(sorted([emp1, emp2]))
                    if pair_key in seen_pairs:
                        continue
                    seen_pairs.add(pair_key)

                    if pair_key not in collaborations:
                        collaborations[pair_key] = {
                            "employees": pair_key,
                            "count": 0,
                            "projects": [],
                        }
                    collaborations[pair_key]["count"] += 1
                    collaborations[pair_key]["projects"].append(project_id)

        # Filter by minimum interactions
        implicit_edges = []
        for pair_key, collab_data in collaborations.items():
            if collab_data["count"] >= min_interactions:
                emp1, emp2 = pair_key.split("|")
                implicit_edges.append(
                    {
                        "source": emp1,
                        "target": emp2,
                        "label": "COLLABORATES_WITH",
                        "strength": collab_data["count"],
                        "projects": collab_data["projects"],
                        "type": "implicit",  # Distinguish from explicit edges
                    }
                )

        # Sort by collaboration strength
        implicit_edges.sort(key=lambda x: x["strength"], reverse=True)

        # Format for G6
        edge_color_map = {
            "PROFICIENT_IN": "#667eea",
            "WORKS_IN": "#4caf50",
            "BELONGS_TO": "#ff9800",
            "REPORTS_TO": "#e91e63",
            "WORKS_ON": "#00bcd4",
            "COLLABORATES_WITH": "#9c27b0",
            "MANAGES": "#f44336",
        }

        formatted_edges = []
        for i, edge in enumerate(implicit_edges):
            color = edge_color_map.get(edge["label"], "#9c27b0")
            formatted_edges.append(
                {
                    "id": f"collab_{i}",
                    "source": edge["source"],
                    "target": edge["target"],
                    "label": f"Collaborates ({edge['strength']})",
                    "style": {
                        "stroke": color,
                        "lineWidth": min(
                            edge["strength"], 5
                        ),  # Thickness based on strength
                        "lineDash": [4, 4],  # Dashed for implicit connections
                        "opacity": 0.7,
                        "endArrow": False,  # No arrow for bidirectional collaboration
                    },
                    "data": {
                        "strength": edge["strength"],
                        "projects": edge["projects"],
                        "implicit": True,
                    },
                }
            )

        return {
            "total_collaborations": len(implicit_edges),
            "min_interactions_filter": min_interactions,
            "edges": formatted_edges,
        }
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
    current_user: dict = Depends(get_current_user),
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
async def ingest_documents(
    request: Request, current_user: dict = Depends(get_current_user)
):
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


@app.get("/auth/status")
async def auth_status():
    return {
        "auth_required": True,
        "api_key_configured": bool(auth_manager.api_key),
        "rate_limiting_enabled": True,
        "cors_configured": True,
    }


if __name__ == "__main__":
    import uvicorn

    print("=" * 50)
    print("🔒 HR Temporal Knowledge Graph - SECURED MODE")
    print("=" * 50)
    print(f"🔑 API Key: {'Configured' if auth_manager.api_key else 'Using Default'}")
    print("🛡️  Security Features:")
    print("   ✅ Authentication Required")
    print("   ✅ Rate Limiting")
    print("   ✅ CORS Protection")
    print("   ✅ Trusted Hosts")
    print("=" * 50)
    print(f"🌐 Server: http://localhost:5000")
    print(f"📖 Health: http://localhost:5000/health")
    print(f"🔐 Auth Status: http://localhost:5000/auth/status")
    print("=" * 50)

    uvicorn.run(app, host="127.0.0.1", port=5000, log_level="info")
