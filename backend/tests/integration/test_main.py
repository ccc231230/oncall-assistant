"""
主应用级别集成测试 — SPA fallback、CORS、根路由。
"""


class TestSPAFallback:
    """SPA catch-all 路由测试。"""

    def test_root_redirects_to_spa(self, client):
        """GET / 返回前端页面（SPA index.html 或 fallback HTML）。"""
        response = client.get("/")

        assert response.status_code == 200
        content_type = response.headers.get("content-type", "")
        # Either returns the built SPA or the fallback HTML
        assert "text/html" in content_type

    def test_v1_serves_spa(self, client):
        """GET /v1 返回 SPA（不触发 API search）。"""
        response = client.get("/v1")

        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_v2_serves_spa(self, client):
        """GET /v2 返回 SPA。"""
        response = client.get("/v2")

        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_v3_serves_spa(self, client):
        """GET /v3 返回 SPA。"""
        response = client.get("/v3")

        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_nonexistent_path_returns_spa(self, client):
        """GET /nonexistent 触发 catch-all，返回 index.html。"""
        response = client.get("/nonexistent")

        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")


class TestCORS:
    """CORS 预检请求测试。"""

    def test_options_search_returns_200(self, client):
        """OPTIONS /v1/search 预检请求返回 200（带 CORS preflight 头）。"""
        response = client.options(
            "/v1/search",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )

        assert response.status_code == 200
        # CORS headers should be present
        headers = response.headers
        assert "access-control-allow-origin" in headers
        assert "access-control-allow-methods" in headers

    def test_options_documents_returns_200(self, client):
        """OPTIONS /v1/documents 预检请求返回 200（带 CORS preflight 头）。"""
        response = client.options(
            "/v1/documents",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
            },
        )

        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
