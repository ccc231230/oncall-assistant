from fastapi import APIRouter, Query, HTTPException
from app.core.models import DocumentRequest, DocumentResponse, SearchResponse
from app.core.html_parser import parse_html
from app.v1.es_client import ESClient

router = APIRouter()

# ESClient singleton, set by main.py lifespan
es_client: ESClient | None = None


def set_es_client(client: ESClient) -> None:
    global es_client
    es_client = client


def get_es_client() -> ESClient:
    if es_client is None:
        raise HTTPException(status_code=503, detail="Search service unavailable")
    return es_client


@router.post("/documents", response_model=DocumentResponse, status_code=201)
async def index_document(doc: DocumentRequest):
    """Index a single SOP document."""
    client = get_es_client()
    parsed = parse_html(doc.html)
    await client.index_document(doc.id, parsed["title"], parsed["content"])
    return DocumentResponse(id=doc.id, title=parsed["title"])


@router.get("/search", response_model=SearchResponse)
async def search_documents(q: str = Query(..., description="Search query")):
    """Search documents by keyword query."""
    client = get_es_client()
    result = await client.search(q)
    return SearchResponse(**result)
