"""
Phase 1 API 集成测试 — POST /v1/documents 和 GET /v1/search。

所有外部依赖（Elasticsearch）均通过 mock 替换，不依赖真实 ES 服务。
"""

import json
from fastapi import status


class TestV1IndexDocument:
    """POST /v1/documents — 文档索引接口。"""

    def test_index_document_returns_201(self, client, mock_es_client):
        """传入 HTML 内容，返回 201 和正确的 id、title。"""
        html_content = "<html><head><title>后端服务 On-Call SOP</title></head><body><p>处理步骤</p></body></html>"

        payload = {"id": "sop-001", "html": html_content}
        response = client.post("/v1/documents", json=payload)

        assert response.status_code == status.HTTP_201_CREATED
        body = response.json()
        assert body["id"] == "sop-001"
        assert "SOP" in body["title"]

    def test_index_document_calls_es(self, client, mock_es_client):
        """验证 index_document 被调用且参数正确。"""
        mock_es_client.index_document.reset_mock()

        html = "<html><head><title>Test</title></head><body><p>Hello</p></body></html>"
        payload = {"id": "test-001", "html": html}
        client.post("/v1/documents", json=payload)

        mock_es_client.index_document.assert_called_once()
        call_args = mock_es_client.index_document.call_args
        assert call_args[0][0] == "test-001"  # doc_id
        assert call_args[0][1] == "Test"       # title
        assert "Hello" in call_args[0][2]       # content


class TestV1Search:
    """GET /v1/search?q= — 关键词搜索接口。"""

    def test_search_OOM_returns_sop001(self, client, mock_es_client):
        """搜索 "OOM" 返回 sop-001。"""
        mock_es_client.search.return_value = {
            "query": "OOM",
            "results": [
                {
                    "id": "sop-001",
                    "title": "后端服务 On-Call SOP",
                    "snippet": "Java服务出现<mark>OOM</mark>崩溃时...",
                    "score": 3.5,
                }
            ],
        }

        response = client.get("/v1/search", params={"q": "OOM"})

        assert response.status_code == 200
        body = response.json()
        assert body["query"] == "OOM"
        assert len(body["results"]) == 1
        assert body["results"][0]["id"] == "sop-001"
        assert body["results"][0]["score"] == 3.5

    def test_search_fault_returns_multiple(self, client, mock_es_client):
        """搜索 "故障" 返回多个文档。"""
        mock_es_client.search.return_value = {
            "query": "故障",
            "results": [
                {"id": "sop-001", "title": "后端服务", "snippet": "...故障...", "score": 2.0},
                {"id": "sop-004", "title": "SRE", "snippet": "...故障...", "score": 1.5},
                {"id": "sop-006", "title": "数据平台", "snippet": "...故障...", "score": 1.2},
            ],
        }

        response = client.get("/v1/search", params={"q": "故障"})

        assert response.status_code == 200
        body = response.json()
        assert len(body["results"]) >= 2
        ids = [r["id"] for r in body["results"]]
        assert "sop-001" in ids

    def test_search_replication_returns_empty(self, client, mock_es_client):
        """
        搜索 "replication" 返回空结果。
        README 验证用例：该词仅在 script 标签内，已被 decompose。
        """
        mock_es_client.search.return_value = {
            "query": "replication",
            "results": [],
        }

        response = client.get("/v1/search", params={"q": "replication"})

        assert response.status_code == 200
        body = response.json()
        assert body["results"] == []

    def test_search_CDN_returns_sop003_and_sop010(self, client, mock_es_client):
        """搜索 "CDN" 返回 sop-003 和 sop-010。"""
        mock_es_client.search.return_value = {
            "query": "CDN",
            "results": [
                {"id": "sop-003", "title": "前端Web", "snippet": "...CDN...", "score": 2.1},
                {"id": "sop-010", "title": "网络与CDN", "snippet": "...CDN...", "score": 1.8},
            ],
        }

        response = client.get("/v1/search", params={"q": "CDN"})

        assert response.status_code == 200
        body = response.json()
        ids = {r["id"] for r in body["results"]}
        assert ids == {"sop-003", "sop-010"}

    def test_search_ampersand_query(self, client, mock_es_client):
        """搜索 & 字符：URL 中的 %26 被正确 decode 为 &。"""
        mock_es_client.search.return_value = {
            "query": "&",
            "results": [
                {"id": "sop-003", "title": "前端", "snippet": "...CDN & cache...", "score": 1.0},
            ],
        }

        # Send %26 as the URL-encoded & — FastAPI/Starlette auto-decodes
        response = client.get("/v1/search", params={"q": "&"})

        assert response.status_code == 200
        body = response.json()
        assert body["query"] == "&"
        assert len(body["results"]) >= 1

    def test_search_snippet_contains_mark(self, client, mock_es_client):
        """验证 snippet 包含 <mark> 高亮标签。"""
        mock_es_client.search.return_value = {
            "query": "OOM",
            "results": [
                {
                    "id": "sop-001",
                    "title": "后端服务",
                    "snippet": "Java服务出现<mark>OOM</mark>崩溃时需要...",
                    "score": 3.5,
                }
            ],
        }

        response = client.get("/v1/search", params={"q": "OOM"})

        assert response.status_code == 200
        body = response.json()
        snippet = body["results"][0]["snippet"]
        assert "<mark>OOM</mark>" in snippet

    def test_search_missing_query_returns_422(self, client):
        """缺少 q 参数时返回 422 Unprocessable Entity。"""
        response = client.get("/v1/search")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
