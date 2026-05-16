"""
E2E tests for Phase 1 keyword search flow (Elasticsearch).

Covers:
- Typing "OOM" and verifying results appear with highlights
- Basic search with result display
- Empty search result handling
- Search UI elements and interactions
"""

from playwright.sync_api import Page, expect


class TestV1SearchFlow:
    """End-to-end Phase 1 keyword search tests."""

    def test_search_OOM_shows_backend_results(self, page: Page) -> None:
        """输入 "OOM" 搜索，验证结果列表出现且标题包含 "后端服务"。"""
        page.goto("/v1", wait_until="networkidle")

        # Type query
        search_input = page.locator('[data-testid="search-input"]')
        search_input.fill("OOM")
        expect(search_input).to_have_value("OOM")

        # Click search
        page.locator('[data-testid="search-button"]').click()

        # Wait for results to load (network idle after fetch)
        page.wait_for_load_state("networkidle")

        # Verify results container has at least one result card
        results = page.locator('[data-testid="search-results"]')
        result_cards = results.locator('[data-testid="result-card"]')
        expect(result_cards.first).to_be_visible(timeout=10000)

        # Verify the first result title mentions 后端服务 (sop-001)
        first_title = result_cards.first.locator('[data-testid="result-title"]')
        expect(first_title).to_contain_text("后端服务")

        # Verify result count message appears
        expect(page.locator('[data-testid="search-result-count"]')).to_be_visible()

    def test_search_results_contain_mark_highlight(self, page: Page) -> None:
        """搜索 "OOM" 后验证结果卡片 snippet 包含 <mark> 高亮标签。"""
        page.goto("/v1", wait_until="networkidle")

        # Search for OOM
        page.locator('[data-testid="search-input"]').fill("OOM")
        page.locator('[data-testid="search-button"]').click()
        page.wait_for_load_state("networkidle")

        # Get the first result card's snippet
        first_card = page.locator('[data-testid="result-card"]').first
        expect(first_card).to_be_visible(timeout=10000)

        snippet = first_card.locator('[data-testid="result-snippet"]')
        # The snippet should contain <mark> element (rendered HTML)
        # Playwright locator can find elements inside shadow-dom-like innerHTML
        mark = snippet.locator("mark")
        expect(mark.first).to_be_visible()

    def test_search_replication_returns_empty(self, page: Page) -> None:
        """搜索 "replication" 返回空结果或显示 "未找到相关结果"。
        Note: "replication" only appears in <script> tags, removed by parser.
        """
        page.goto("/v1", wait_until="networkidle")

        page.locator('[data-testid="search-input"]').fill("replication")
        page.locator('[data-testid="search-button"]').click()
        page.wait_for_load_state("networkidle")

        # Either empty state or zero results
        empty_state = page.locator('[data-testid="search-empty"]')
        result_cards = page.locator('[data-testid="result-card"]')

        # At least one of these should be true
        has_empty = empty_state.is_visible()
        has_no_cards = result_cards.count() == 0
        assert has_empty or has_no_cards, (
            "Expected empty state or zero result cards for 'replication' query"
        )

    def test_search_CDN_returns_sop003_and_sop010(self, page: Page) -> None:
        """搜索 "CDN" 验证返回结果包含 sop-003 和 sop-010。"""
        page.goto("/v1", wait_until="networkidle")

        page.locator('[data-testid="search-input"]').fill("CDN")
        page.locator('[data-testid="search-button"]').click()
        page.wait_for_load_state("networkidle")

        result_cards = page.locator('[data-testid="result-card"]')
        expect(result_cards.first).to_be_visible(timeout=10000)

        # Collect document IDs from result cards
        count = result_cards.count()
        doc_ids: set[str] = set()
        for i in range(count):
            card_text = result_cards.nth(i).inner_text()
            # Document ID appears as "文档 ID: sop-XXX" in the card
            for prefix in ["sop-003", "sop-010"]:
                if prefix in card_text:
                    doc_ids.add(prefix)

        assert "sop-003" in doc_ids, f"Expected sop-003 in results, got: {doc_ids}"
        assert "sop-010" in doc_ids, f"Expected sop-010 in results, got: {doc_ids}"

    def test_search_shows_BM25_score_label(self, page: Page) -> None:
        """验证搜索结果卡片显示 BM25 分数字段。"""
        page.goto("/v1", wait_until="networkidle")

        page.locator('[data-testid="search-input"]').fill("故障")
        page.locator('[data-testid="search-button"]').click()
        page.wait_for_load_state("networkidle")

        first_card = page.locator('[data-testid="result-card"]').first
        expect(first_card).to_be_visible(timeout=10000)

        # Score badge should contain "BM25"
        score_badge = first_card.locator('[data-testid="result-score"]')
        expect(score_badge).to_contain_text("BM25")
