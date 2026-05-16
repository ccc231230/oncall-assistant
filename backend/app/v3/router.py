from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.core.models import ChatRequest
from app.v3.agent import chat_stream

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
