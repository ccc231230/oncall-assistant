from fastapi import APIRouter, Query, HTTPException
from app.core.models import SearchResponse
from app.v2.faiss_store import FAISSStore

router = APIRouter()

# FAISSStore singleton, set by main.py lifespan
faiss_store: FAISSStore | None = None


def set_faiss_store(store: FAISSStore) -> None:
    global faiss_store
    faiss_store = store


def get_faiss_store() -> FAISSStore:
    if faiss_store is None:
        raise HTTPException(status_code=503, detail="Semantic search service unavailable")
    return faiss_store


@router.get("/search", response_model=SearchResponse)
async def semantic_search(q: str = Query(..., description="Search query")):
    """Semantic search by query meaning."""
    store = get_faiss_store()
    try:
        result = store.search(q)
        return SearchResponse(**result)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
