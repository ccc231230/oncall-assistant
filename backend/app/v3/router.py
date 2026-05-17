from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, UploadFile, File
from fastapi.responses import StreamingResponse
from app.core.config import settings
from app.core.models import ChatRequest, UploadResponse, FileInfo, FileListResponse
from app.v3.agent import chat_stream
from app.v3.tools import save_uploaded_file

router = APIRouter()


@router.post("/chat")
async def agent_chat(req: ChatRequest):
    """Agent chat endpoint with SSE streaming."""
    history = [{"role": h.role, "content": h.content} for h in req.history]

    return StreamingResponse(
        chat_stream(req.message, history),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """Upload an SOP HTML file to the data directory."""
    result = save_uploaded_file(file)
    return result


@router.get("/files", response_model=FileListResponse)
async def list_files():
    """List all HTML files in the data directory."""
    data_dir = Path(settings.DATA_DIR)
    files: list[FileInfo] = []
    if data_dir.exists():
        for f in sorted(data_dir.glob("*.html"), key=lambda x: x.stat().st_mtime, reverse=True):
            stat = f.stat()
            files.append(FileInfo(
                name=f.name,
                size=stat.st_size,
                modified=datetime.fromtimestamp(stat.st_mtime).isoformat(),
            ))
    return FileListResponse(files=files)
