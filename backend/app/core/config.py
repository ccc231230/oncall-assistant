from pathlib import Path
from pydantic_settings import BaseSettings

# Repo root: go up 4 levels from this file (core/config.py → core/ → app/ → backend/ → repo/)
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class Settings(BaseSettings):
    # Data
    DATA_DIR: str = str(_REPO_ROOT / "data")

    # Elasticsearch
    ES_HOST: str = "http://localhost:9200"
    ES_INDEX: str = "oncall_docs"

    # FAISS / Embedding
    EMBEDDING_MODEL: str = "paraphrase-multilingual-MiniLM-L12-v2"
    FAISS_INDEX_PATH: str = str(Path(DATA_DIR) / "faiss.index")
    FAISS_METADATA_PATH: str = str(Path(DATA_DIR) / "faiss_metadata.json")

    # Kimi API
    KIMI_API_KEY: str = "sk-placeholder"
    KIMI_BASE_URL: str = "https://api.moonshot.cn/v1"
    KIMI_MODEL: str = "kimi-k2.6"

    # Agent
    MAX_AGENT_TURNS: int = 5

    # File upload
    MAX_UPLOAD_SIZE_MB: int = 10


settings = Settings()
