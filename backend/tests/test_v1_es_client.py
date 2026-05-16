"""Tests for app.v1.es_client.ESClient — all mocked, no real ES required."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.v1.es_client import ESClient


@pytest.fixture
def mock_es():
    """Mock AsyncElasticsearch instance."""
    mock = MagicMock()
    mock.indices = MagicMock()
    mock.indices.exists = AsyncMock()
    mock.indices.create = AsyncMock()
    mock.index = AsyncMock()
    mock.search = AsyncMock()
    mock.close = AsyncMock()
    return mock


@pytest.fixture
def client(mock_es):
    """ESClient with mocked AsyncElasticsearch."""
    with patch("app.v1.es_client.AsyncElasticsearch", return_value=mock_es):
        c = ESClient()
        c.es = mock_es
        return c


class TestESClientCreateIndex:
    """Tests for create_index method."""

    @pytest.mark.asyncio
    async def test_create_index_when_not_exists(self, client, mock_es):
        """index 不存在时调用 es.indices.create。"""
        mock_es.indices.exists.return_value = False

        await client.create_index()

        mock_es.indices.exists.assert_called_once()
        mock_es.indices.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_index_when_already_exists(self, client, mock_es):
        """index 已存在时不重复创建。"""
        mock_es.indices.exists.return_value = True

        await client.create_index()

        mock_es.indices.exists.assert_called_once()
        mock_es.indices.create.assert_not_called()


class TestESClientIndexDocument:
    """Tests for index_document method."""

    @pytest.mark.asyncio
    async def test_index_document_correct_body(self, client, mock_es):
        """验证传入 ES 的 body 包含正确的字段。"""
        await client.index_document("sop-001", "Test Title", "Test content text")

        call_kwargs = mock_es.index.call_args.kwargs
        assert call_kwargs["index"] == "oncall_docs"
        assert call_kwargs["id"] == "sop-001"
        assert call_kwargs["body"]["id"] == "sop-001"
        assert call_kwargs["body"]["title"] == "Test Title"
        assert call_kwargs["body"]["content"] == "Test content text"


class TestESClientSearch:
    """Tests for search method."""

    @pytest.mark.asyncio
    async def test_search_with_hits_oom(self, client, mock_es):
        """搜索 "OOM" 返回 sop-001。"""
        mock_es.search.return_value = {
            "hits": {
                "hits": [
                    {
                        "_score": 3.5,
                        "_source": {
                            "id": "sop-001",
                            "title": "后端服务 On-Call SOP",
                            "content": "Java服务出现OutOfMemoryError时...",
                        },
                        "highlight": {
                            "content": ["Java服务出现<mark>OOM</mark>崩溃时..."],
                        },
                    }
                ]
            }
        }

        result = await client.search("OOM")

        assert result["query"] == "OOM"
        assert len(result["results"]) == 1
        assert result["results"][0]["id"] == "sop-001"
        assert "<mark>OOM</mark>" in result["results"][0]["snippet"]
        assert result["results"][0]["score"] == 3.5

    @pytest.mark.asyncio
    async def test_search_empty_hits(self, client, mock_es):
        """搜索 "replication" 返回空结果。"""
        mock_es.search.return_value = {"hits": {"hits": []}}

        result = await client.search("replication")

        assert result["query"] == "replication"
        assert result["results"] == []

    @pytest.mark.asyncio
    async def test_search_ampersand_query(self, client, mock_es):
        """搜索 "&" 字符：验证查询正确传递给 ES。"""
        mock_es.search.return_value = {"hits": {"hits": []}}

        await client.search("&")

        # Verify the search was called with "&" in the multi_match query
        call_args = mock_es.search.call_args.kwargs
        assert call_args["body"]["query"]["multi_match"]["query"] == "&"

    @pytest.mark.asyncio
    async def test_search_result_no_highlight(self, client, mock_es):
        """ES 无 highlight 时，fallback 到 content 前 200 字符。"""
        mock_es.search.return_value = {
            "hits": {
                "hits": [
                    {
                        "_score": 1.0,
                        "_source": {
                            "id": "sop-002",
                            "title": "DB SOP",
                            "content": "A" * 300,
                        },
                    }
                ]
            }
        }

        result = await client.search("test")

        assert len(result["results"]) == 1
        # Should be content truncated to 200 chars
        assert len(result["results"][0]["snippet"]) == 200


class TestESClientClose:
    """Tests for close method."""

    @pytest.mark.asyncio
    async def test_close(self, client, mock_es):
        """关闭 ES 客户端连接。"""
        await client.close()
        mock_es.close.assert_called_once()
