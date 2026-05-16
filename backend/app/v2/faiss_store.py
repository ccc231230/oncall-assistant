import json
import logging
from pathlib import Path
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from app.core.config import settings
from app.core.html_parser import parse_html

logger = logging.getLogger(__name__)


class FAISSStore:
    def __init__(self):
        self.model: SentenceTransformer | None = None
        self.index: faiss.IndexFlatIP | None = None
        self.metadata: list[dict] = []  # [{id, title, snippet}]

        self._index_path = Path(settings.FAISS_INDEX_PATH)
        self._meta_path = Path(settings.FAISS_METADATA_PATH)

    def load_model(self) -> None:
        """Load the sentence-transformers model."""
        logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
        self.model = SentenceTransformer(settings.EMBEDDING_MODEL)
        logger.info("Model loaded successfully")

    def _encode(self, texts: list[str]) -> np.ndarray:
        """Encode texts to normalized embeddings."""
        if self.model is None:
            raise RuntimeError("Model not loaded")
        embeddings = self.model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
        # L2 normalize for cosine similarity via inner product
        faiss.normalize_L2(embeddings)
        return embeddings

    def build_index(self, data_dir: str) -> None:
        """Build FAISS index from all SOP HTML files in data_dir."""
        if self.model is None:
            raise RuntimeError("Model not loaded")

        data_path = Path(data_dir)
        html_files = sorted(data_path.glob("*.html"))
        if not html_files:
            logger.warning(f"No HTML files found in {data_dir}")
            return

        texts = []
        self.metadata = []

        for filepath in html_files:
            doc_id = filepath.stem
            html = filepath.read_text(encoding="utf-8")
            parsed = parse_html(html)

            # Use title + first 500 chars of content for embedding
            text_for_embed = f"{parsed['title']}\n{parsed['content'][:500]}"
            texts.append(text_for_embed)

            snippet = parsed["content"][:200].replace("\n", " ")
            self.metadata.append(
                {
                    "id": doc_id,
                    "title": parsed["title"],
                    "snippet": snippet,
                }
            )

        # Encode and build index
        embeddings = self._encode(texts)
        dim = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dim)
        self.index.add(embeddings)

        logger.info(f"Built FAISS index with {len(self.metadata)} documents, dim={dim}")

    def save(self) -> None:
        """Save index and metadata to disk."""
        if self.index is None:
            return
        self._index_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(self._index_path))
        with open(self._meta_path, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, ensure_ascii=False)
        logger.info(f"Saved FAISS index to {self._index_path}")

    def load(self) -> bool:
        """Load index and metadata from disk. Returns True if successful."""
        if not self._index_path.exists() or not self._meta_path.exists():
            return False
        try:
            self.index = faiss.read_index(str(self._index_path))
            with open(self._meta_path, "r", encoding="utf-8") as f:
                self.metadata = json.load(f)
            logger.info(f"Loaded FAISS index with {len(self.metadata)} documents")
            return True
        except Exception as e:
            logger.warning(f"Failed to load FAISS index: {e}")
            return False

    def search(self, query: str, k: int = 5) -> dict:
        """Semantic search. Returns {query, results} with cosine similarity scores."""
        if self.index is None or self.model is None:
            raise RuntimeError("Index or model not initialized")

        query_embedding = self._encode([query])
        scores, indices = self.index.search(query_embedding, k)

        results = []
        for idx, score in zip(indices[0], scores[0]):
            if idx < 0 or idx >= len(self.metadata):
                continue
            meta = self.metadata[idx]
            results.append(
                {
                    "id": meta["id"],
                    "title": meta["title"],
                    "snippet": meta["snippet"],
                    "score": round(float(score), 4),
                }
            )

        return {"query": query, "results": results}
