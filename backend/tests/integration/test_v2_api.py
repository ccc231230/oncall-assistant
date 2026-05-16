"""
Phase 2 API 集成测试 — GET /v2/search?q= 语义搜索接口。

mock FAISSStore.search() 返回值，验证 API 响应格式。
"""

from fastapi import status


class TestV2SemanticSearch:
    """GET /v2/search?q= — 语义搜索接口。"""

    def test_search_server_down(self, client, mock_faiss_store):
        """搜索 "服务器挂了" 返回 sop-001（后端）和 sop-004（SRE）靠前。"""
        mock_faiss_store.search.return_value = {
            "query": "服务器挂了",
            "results": [
                {
                    "id": "sop-001",
                    "title": "后端服务 On-Call SOP",
                    "snippet": "后端服务值班工程师...",
                    "score": 0.92,
                },
                {
                    "id": "sop-004",
                    "title": "SRE基础设施 On-Call SOP",
                    "snippet": "K8s集群问题...",
                    "score": 0.88,
                },
                {
                    "id": "sop-006",
                    "title": "数据平台 On-Call SOP",
                    "snippet": "数据管道故障...",
                    "score": 0.45,
                },
            ],
        }

        response = client.get("/v2/search", params={"q": "服务器挂了"})

        assert response.status_code == 200
        body = response.json()
        assert body["query"] == "服务器挂了"
        results = body["results"]
        assert len(results) >= 2
        # sop-001 should be first with highest score
        assert results[0]["id"] == "sop-001"
        assert results[0]["score"] == 0.92
        # Verify descending score order
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_search_hacker_attack(self, client, mock_faiss_store):
        """搜索 "黑客攻击" 返回 sop-005（安全团队）排名第一。"""
        mock_faiss_store.search.return_value = {
            "query": "黑客攻击",
            "results": [
                {"id": "sop-005", "title": "信息安全 On-Call SOP", "snippet": "...", "score": 0.95},
                {"id": "sop-010", "title": "网络与CDN", "snippet": "...", "score": 0.62},
                {"id": "sop-004", "title": "SRE", "snippet": "...", "score": 0.51},
            ],
        }

        response = client.get("/v2/search", params={"q": "黑客攻击"})

        assert response.status_code == 200
        body = response.json()
        assert len(body["results"]) >= 1
        assert body["results"][0]["id"] == "sop-005"
        assert body["results"][0]["score"] > 0.9

    def test_search_ml_problem(self, client, mock_faiss_store):
        """搜索 "机器学习模型出问题" 返回 sop-008（AI算法）排名第一。"""
        mock_faiss_store.search.return_value = {
            "query": "机器学习模型出问题",
            "results": [
                {"id": "sop-008", "title": "AI与算法 On-Call SOP", "snippet": "...", "score": 0.91},
                {"id": "sop-006", "title": "数据平台", "snippet": "...", "score": 0.55},
                {"id": "sop-001", "title": "后端服务", "snippet": "...", "score": 0.30},
            ],
        }

        response = client.get("/v2/search", params={"q": "机器学习模型出问题"})

        assert response.status_code == 200
        body = response.json()
        assert body["results"][0]["id"] == "sop-008"

    def test_search_empty_index(self, client, mock_faiss_store):
        """空索引返回 results == []。"""
        mock_faiss_store.search.return_value = {
            "query": "任意查询",
            "results": [],
        }

        response = client.get("/v2/search", params={"q": "任意查询"})

        assert response.status_code == 200
        body = response.json()
        assert body["results"] == []

    def test_search_missing_query_returns_422(self, client):
        """缺少 q 参数时返回 422。"""
        response = client.get("/v2/search")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
