from pydantic import BaseModel
from typing import Optional


class DocumentRequest(BaseModel):
    id: str
    html: str


class DocumentResponse(BaseModel):
    id: str
    title: str


class SearchResult(BaseModel):
    id: str
    title: str
    snippet: str
    score: float


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []


class SSEEvent(BaseModel):
    event: str  # "thought" | "tool_call" | "tool_result" | "answer" | "error"
    data: dict
