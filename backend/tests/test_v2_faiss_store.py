"""Tests for app.v2.faiss_store.FAISSStore — all mocked, no real model required."""

import numpy as np
import faiss
import pytest
from unittest.mock import MagicMock, patch

from app.v2.faiss_store import FAISSStore


@pytest.fixture
def mock_model():
    """Mock SentenceTransformer with fixed 384-dim embeddings."""
    model = MagicMock()
    model.encode.return_value = np.array([[0.5, 0.5, 0.5, 0.5]], dtype=np.float32)
    return model


@pytest.fixture
def store(mock_model):
    """FAISSStore with mocked model loaded."""
    with patch("app.v2.faiss_store.SentenceTransformer", return_value=mock_model):
        s = FAISSStore()
        s.load_model()
        return s


class TestFAISSStoreBuild:
    """Tests for build_index."""

    def test_build_index_ntotal(self, store, mock_model, tmp_path):
        """build_index：验证 index.ntotal 等于文档数。"""
        # Create fake HTML files
        for i in range(1, 4):
            (tmp_path / f"sop-{i:03d}.html").write_text(
                f"<html><head><title>Doc {i}</title></head>"
                f"<body><p>Content {i}</p></body></html>",
                encoding="utf-8",
            )

        # Mock encode to return fixed vectors of correct dimension
        mock_model.encode.return_value = np.array(
            [[0.1] * 384, [0.2] * 384, [0.3] * 384], dtype=np.float32
        )

        store.build_index(str(tmp_path))

        assert store.index is not None
        assert store.index.ntotal == 3
        assert len(store.metadata) == 3
        assert store.metadata[0]["id"] == "sop-001"
        assert store.metadata[1]["id"] == "sop-002"
        assert store.metadata[2]["id"] == "sop-003"

    def test_l2_normalization(self, store, mock_model, tmp_path):
        """向量归一化：验证传入 FAISS 的向量 L2 范数为 1。"""
        (tmp_path / "sop-001.html").write_text(
            "<html><head><title>Test</title></head><body><p>Content</p></body></html>",
            encoding="utf-8",
        )

        # Use a non-normalized vector
        raw_vector = np.array([[3.0, 4.0, 0.0] * 128], dtype=np.float32)  # 384-dim
        mock_model.encode.return_value = raw_vector

        store.build_index(str(tmp_path))

        # Read back the stored vector from FAISS
        vectors = np.zeros((1, store.index.d), dtype=np.float32)
        store.index.reconstruct(0, vectors[0])

        # L2 norm of [3,4,0,...] = 5, after normalize_L2 = [0.6, 0.8, 0, ...]
        norm = np.linalg.norm(vectors[0])
        assert abs(norm - 1.0) < 0.01, f"Expected L2 norm ~1.0, got {norm}"

    def test_search_results_sorted(self, store, mock_model, tmp_path):
        """semantic_search：验证结果按 score 降序排列。"""
        # Create 3 documents
        for i in range(1, 4):
            (tmp_path / f"doc-{i}.html").write_text(
                f"<html><head><title>Doc {i}</title></head>"
                f"<body><p>Content {i}</p></body></html>",
                encoding="utf-8",
            )

        # Embeddings: distinct directions so L2 norm preserves ranking
        doc_vectors = np.array(
            [
                [0.9, 0.0] + [0.0] * 382,  # doc-1: strongly aligned with query dim-1
                [0.7, 0.7] + [0.0] * 382,  # doc-2: partial alignment
                [0.0, 0.9] + [0.0] * 382,  # doc-3: orthogonal to query dim-1
            ],
            dtype=np.float32,
        )
        mock_model.encode.return_value = doc_vectors
        store.build_index(str(tmp_path))

        # Query: biased strictly toward first dimension
        query_vector = np.array([[1.0] + [0.0] * 383], dtype=np.float32)
        mock_model.encode.return_value = query_vector

        results = store.search("test query", k=3)

        assert len(results["results"]) == 3
        assert results["results"][0]["id"] == "doc-1"  # doc-1 has highest inner product
        scores = [r["score"] for r in results["results"]]
        assert scores == sorted(scores, reverse=True), f"Scores not descending: {scores}"

    def test_save_and_load(self, store, mock_model, tmp_path):
        """save/load：保存到磁盘后再加载，数据一致。"""
        (tmp_path / "sop-001.html").write_text(
            "<html><head><title>Test</title></head><body><p>Content</p></body></html>",
            encoding="utf-8",
        )
        mock_model.encode.return_value = np.array([[1.0] * 384], dtype=np.float32)
        store.build_index(str(tmp_path))

        # Override index paths to use temp directory
        store._index_path = tmp_path / "faiss.index"
        store._meta_path = tmp_path / "faiss_meta.json"
        store.save()

        # Create a new store and load
        new_store = FAISSStore()
        new_store._index_path = tmp_path / "faiss.index"
        new_store._meta_path = tmp_path / "faiss_meta.json"

        loaded = new_store.load()
        assert loaded is True
        assert new_store.index is not None
        assert new_store.index.ntotal == 1
        assert new_store.metadata[0]["id"] == "sop-001"

    def test_load_when_no_files(self):
        """索引文件不存在时 load 返回 False。"""
        store = FAISSStore()
        store._index_path = store._index_path.parent / "nonexistent_faiss.index"
        store._meta_path = store._meta_path.parent / "nonexistent_meta.json"

        result = store.load()
        assert result is False

    def test_build_empty_dir(self, store, mock_model, tmp_path):
        """空目录 build_index：不应报错，index 保持 None。"""
        store.build_index(str(tmp_path))
        assert store.index is None
        assert store.metadata == []

    def test_search_before_build(self, store):
        """index 未初始化时 search 抛出 RuntimeError。"""
        with pytest.raises(RuntimeError, match="Index or model not initialized"):
            store.search("test")

    def test_encode_without_model(self):
        """模型未加载时 _encode 抛出 RuntimeError。"""
        store = FAISSStore()
        with pytest.raises(RuntimeError, match="Model not loaded"):
            store._encode(["test"])
