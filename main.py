from fastapi import FastAPI, HTTPException, UploadFile, File
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


app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def read_root():
    return FileResponse("static/index.html")


@app.post("/query")
async def query(request: QueryRequest):
    try:
        if not graph:
            raise HTTPException(
                status_code=503, detail="Service unavailable - graph not initialized"
            )

        if not request.query or len(request.query.strip()) == 0:
            raise HTTPException(status_code=400, detail="Query cannot be empty")

        result = await graph.query_hybrid(request.query)
        return {"result": result}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/history/{employee_name}")
async def history(employee_name: str):
    try:
        if not graph:
            raise HTTPException(
                status_code=503, detail="Service unavailable - graph not initialized"
            )

        if not employee_name or len(employee_name.strip()) == 0:
            raise HTTPException(status_code=400, detail="Employee name cannot be empty")

        result = await graph.get_employee_history(employee_name)
        return {"history": result}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/graph")
async def get_graph():
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
async def upload_file(file: UploadFile = File(...)):
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

        return {"filename": sanitized_filename, "status": "uploaded"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.post("/ingest")
async def ingest_documents():
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5000)
