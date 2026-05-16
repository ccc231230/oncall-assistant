"""
E2E tests for Phase 2 semantic search flow (FAISS).

Covers:
- Natural language query "服务器挂了" returns sop-001 / sop-004
- Score label shows "语义相似度"
- Empty results for out-of-domain queries
- Results sorted by descending similarity
"""

from playwright.sync_api import Page, expect


class TestV2SearchFlow:
    """End-to-end Phase 2 semantic search tests."""

    def test_search_server_down_returns_backend_sre(self, page: Page) -> None:
        """输入 "服务器挂了"，验证返回 sop-001（后端）或 sop-004（SRE）在前列。"""
        page.goto("/v2", wait_until="networkidle")

        page.locator('[data-testid="search-input"]').fill("服务器挂了")
        page.locator('[data-testid="search-button"]').click()
        page.wait_for_load_state("networkidle")

        result_cards = page.locator('[data-testid="result-card"]')
        expect(result_cards.first).to_be_visible(timeout=10000)

        # First result should be sop-001 (most relevant for backend issues)
        first_id_text = result_cards.first.inner_text()
        assert "sop-001" in first_id_text or "sop-004" in first_id_text, (
            f"Expected sop-001 or sop-004 as top result, got: {first_id_text[:100]}"
        )

    def test_search_returns_semantic_similarity_score(self, page: Page) -> None:
        """验证结果卡片显示 "语义相似度" 分数字段。"""
        page.goto("/v2", wait_until="networkidle")

        page.locator('[data-testid="search-input"]').fill("服务器挂了")
        page.locator('[data-testid="search-button"]').click()
        page.wait_for_load_state("networkidle")

        first_card = page.locator('[data-testid="result-card"]').first
        expect(first_card).to_be_visible(timeout=10000)

        score_badge = first_card.locator('[data-testid="result-score"]')
        expect(score_badge).to_contain_text("语义相似度")

    def test_search_results_sorted_by_score_desc(self, page: Page) -> None:
        """验证返回结果按语义相似度分数降序排列。"""
        page.goto("/v2", wait_until="networkidle")

        page.locator('[data-testid="search-input"]').fill("黑客攻击")
        page.locator('[data-testid="search-button"]').click()
        page.wait_for_load_state("networkidle")

        result_cards = page.locator('[data-testid="result-card"]')
        expect(result_cards.first).to_be_visible(timeout=10000)

        # Extract scores from badges and verify descending order
        count = result_cards.count()
        if count >= 2:
            scores: list[float] = []
            for i in range(count):
                badge_text = result_cards.nth(i).locator('[data-testid="result-score"]').inner_text()
                # Format: "语义相似度: 0.92"
                score_str = badge_text.split(":")[-1].strip()
                scores.append(float(score_str))

            assert scores == sorted(scores, reverse=True), (
                f"Scores not in descending order: {scores}"
            )

    def test_search_empty_for_unrelated_query(self, page: Page) -> None:
        """搜索不相关内容时显示空结果或初始状态。"""
        page.goto("/v2", wait_until="networkidle")

        page.locator('[data-testid="search-input"]').fill("xyzzy_nonexistent_query_12345")
        page.locator('[data-testid="search-button"]').click()
        page.wait_for_load_state("networkidle")

        # Should show empty state or zero results
        empty_state = page.locator('[data-testid="search-empty"]')
        result_cards = page.locator('[data-testid="result-card"]')
        assert empty_state.is_visible() or result_cards.count() == 0, (
            "Expected empty state for unrelated query"
        )

    def test_search_page_shows_initial_prompt(self, page: Page) -> None:
        """首次加载 /v2 页面时显示初始提示文案。"""
        page.goto("/v2", wait_until="networkidle")

        initial = page.locator('[data-testid="search-initial"]')
        expect(initial).to_be_visible()
        expect(initial).to_contain_text("用自然语言搜索")
