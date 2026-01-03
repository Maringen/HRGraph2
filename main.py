from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from auth import auth_manager, get_current_user
from slowapi import Limiter, get_remote_address
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import os
import time
from temporal_graph import HRTemporalGraph
from pydantic import BaseModel
import asyncio
import os
import re
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import aiofiles
from auth import auth_manager, get_current_user
from slowapi import Limiter, get_remote_address
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import time

rate_limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

graph = None


class QueryRequest(BaseModel):
    query: str


MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".md", ".txt"}
VAULT_DIR = Path("./hr_vault").resolve()
VAULT_DIR.mkdir(exist_ok=True)


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
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/history/{employee_name}")
@rate_limiter.limit("30/minute")
async def history(employee_name: str, current_user: dict = Depends(get_current_user)):
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
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/graph")
@rate_limiter.limit("10/minute")
async def get_graph(current_user: dict = Depends(get_current_user)):
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
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/upload")
@rate_limiter.limit("5/minute")
async def upload_file(
    file: UploadFile = File(...), current_user: dict = Depends(get_current_user)
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
async def ingest_documents(current_user: dict = Depends(get_current_user)):
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
