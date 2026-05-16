"""
E2E tests for SPA navigation and page rendering.

Covers:
- Automatic redirect from / to /v1
- Navigation bar links switch between Phase 1/2/3
- Direct URL access serves correct pages (SPA fallback)
"""

from playwright.sync_api import Page, expect


class TestSPANavigation:
    """Verify routing and navigation bar behaviour."""

    def test_root_redirects_to_v1(self, page: Page) -> None:
        """访问 / 自动跳转到 /v1 并显示 Phase 1 搜索页。"""
        page.goto("/", wait_until="networkidle")

        # URL should be /v1 after redirect
        expect(page).to_have_url("/v1")
        # Page heading should confirm Phase 1
        expect(page.locator("h2")).to_contain_text("Phase 1")
        # Search form should be visible
        expect(page.locator('[data-testid="search-input"]')).to_be_visible()
        expect(page.locator('[data-testid="search-button"]')).to_be_visible()

    def test_nav_phase1_active_and_route(self, page: Page) -> None:
        """导航栏 Phase 1 链接高亮且 URL 为 /v1。"""
        page.goto("/v2", wait_until="networkidle")

        # Click Phase 1 in nav
        page.locator('[data-testid="nav-phase1"]').click()
        page.wait_for_load_state("networkidle")

        expect(page).to_have_url("/v1")
        expect(page.locator("h2")).to_contain_text("Phase 1")
        # Nav link should have active styling class
        nav = page.locator('[data-testid="nav-phase1"]')
        expect(nav).to_have_class(re.compile(r"bg-blue-600"))

    def test_nav_phase2_renders_semantic_search(self, page: Page) -> None:
        """点击 Phase 2 导航，URL 变为 /v2，显示语义搜索输入框。"""
        page.goto("/v1", wait_until="networkidle")

        page.locator('[data-testid="nav-phase2"]').click()
        page.wait_for_load_state("networkidle")

        expect(page).to_have_url("/v2")
        expect(page.locator("h2")).to_contain_text("Phase 2")
        expect(page.locator('[data-testid="search-input"]')).to_be_visible()
        expect(page.locator('[data-testid="search-button"]')).to_be_visible()

    def test_nav_phase3_renders_chat_interface(self, page: Page) -> None:
        """点击 Phase 3 导航，URL 变为 /v3，显示对话界面。"""
        page.goto("/v1", wait_until="networkidle")

        page.locator('[data-testid="nav-phase3"]').click()
        page.wait_for_load_state("networkidle")

        expect(page).to_have_url("/v3")
        expect(page.locator("h2")).to_contain_text("Phase 3")
        # Chat welcome message should appear
        expect(page.locator('[data-testid="chat-welcome"]')).to_be_visible()
        # Chat input and send button should exist
        expect(page.locator('[data-testid="chat-input"]')).to_be_visible()
        expect(page.locator('[data-testid="chat-send"]')).to_be_visible()

    def test_direct_url_v2_loads_correctly(self, page: Page) -> None:
        """直接访问 /v2 页面正确加载（SPA fallback 测试）。"""
        page.goto("/v2", wait_until="networkidle")

        expect(page).to_have_url("/v2")
        expect(page.locator("h2")).to_contain_text("Phase 2")
        expect(page.locator('[data-testid="search-input"]')).to_be_visible()

    def test_direct_url_v3_loads_correctly(self, page: Page) -> None:
        """直接访问 /v3 页面正确加载（SPA fallback 测试）。"""
        page.goto("/v3", wait_until="networkidle")

        expect(page).to_have_url("/v3")
        expect(page.locator("h2")).to_contain_text("Phase 3")
        expect(page.locator('[data-testid="chat-welcome"]')).to_be_visible()
