import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse

from app.core.config import settings
from app.v1.es_client import ESClient
from app.v1.router import router as v1_router, set_es_client
from app.v2.faiss_store import FAISSStore
from app.v2.router import router as v2_router, set_faiss_store
from app.v3.router import router as v3_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# Singletons
es_client: ESClient | None = None
faiss_store: FAISSStore | None = None


async def _init_faiss_background():
    """Initialize FAISS store in background (model download may be slow)."""
    global faiss_store
    try:
        store = FAISSStore()
        # Run model loading in a thread to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, store.load_model)

        if not store.load():
            logger.info("Building FAISS index from data files...")
            store.build_index(settings.DATA_DIR)
            store.save()
        else:
            logger.info("FAISS index loaded from disk")

        faiss_store = store
        set_faiss_store(faiss_store)
        logger.info("FAISS initialization complete!")
    except Exception as e:
        logger.error(f"Failed to initialize FAISS: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize and cleanup services."""
    global es_client, faiss_store

    # --- Startup ---
    logger.info("Starting On-Call Assistant...")

    # Initialize Elasticsearch
    try:
        es_client = ESClient()
        # Wait for ES to be ready
        for attempt in range(30):
            try:
                if await es_client.es.ping():
                    break
            except Exception:
                pass
            logger.info(f"Waiting for Elasticsearch... (attempt {attempt + 1}/30)")
            await asyncio.sleep(2)
        else:
            logger.error("Elasticsearch not available after 30 attempts")

        await es_client.create_index()
        data_path = Path(settings.DATA_DIR)
        if data_path.exists():
            count = await es_client.index_all_from_data(data_path)
            logger.info(f"Indexed {count} documents to Elasticsearch")
        else:
            logger.warning(f"Data directory not found: {data_path}")

        set_es_client(es_client)
    except Exception as e:
        logger.error(f"Failed to initialize Elasticsearch: {e}")

    # Start FAISS initialization in background (model download may be slow)
    asyncio.create_task(_init_faiss_background())

    logger.info("On-Call Assistant ready!")

    yield

    # --- Shutdown ---
    logger.info("Shutting down...")
    if es_client:
        await es_client.close()


app = FastAPI(
    title="On-Call Assistant",
    description="智能值班助手 - 基于部门 SOP 文档的检索与问答系统",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS - allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(v1_router, prefix="/v1", tags=["Phase 1 - Keyword Search"])
app.include_router(v2_router, prefix="/v2", tags=["Phase 2 - Semantic Search"])
app.include_router(v3_router, prefix="/v3", tags=["Phase 3 - Agent"])

# Path to the SPA
SPA_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
SPA_INDEX = SPA_DIST / "index.html"


@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """
    Catch-all route: serve static files from SPA dist, or fallback to index.html.
    API routes (e.g., /v1/search, /v2/search, /v3/chat) take precedence.
    """
    # Serve actual static files (JS, CSS, etc.)
    requested_path = SPA_DIST / full_path.lstrip("/")
    if requested_path.exists() and requested_path.is_file():
        headers = {"Access-Control-Allow-Origin": "*"}
        # Hashed assets can be cached long-term
        if requested_path.suffix in (".js", ".css", ".woff", ".woff2", ".png", ".svg", ".ico"):
            headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return FileResponse(str(requested_path), headers=headers)

    # Fallback to SPA index.html for client-side routing (never cache)
    if SPA_INDEX.exists():
        return FileResponse(
            str(SPA_INDEX),
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
        )
    else:
        return HTMLResponse(
            content=f"""
            <html>
            <head><title>On-Call Assistant</title></head>
            <body style="font-family: sans-serif; padding: 40px; text-align: center;">
                <h1>On-Call Assistant</h1>
                <p>Frontend not built yet. Run the development server:</p>
                <pre>cd frontend && npm install && npm run dev</pre>
                <hr/>
                <p><strong>API Routes:</strong></p>
                <ul style="list-style: none; padding: 0;">
                    <li><a href="/v1/search?q=OOM">/v1/search?q=OOM</a></li>
                    <li><a href="/v2/search?q=服务器挂了">/v2/search?q=服务器挂了</a></li>
                    <li><a href="/v3">/v3 (Agent Chat)</a></li>
                </ul>
            </body>
            </html>
            """,
            status_code=200,
        )


@app.get("/")
async def root():
    """Redirect to /v1 by serving the SPA."""
    return await serve_spa("")
