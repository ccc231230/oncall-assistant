"""
E2E test fixtures and configuration for Playwright.

Requires:
    pip install pytest-playwright
    playwright install chromium

Usage:
    docker-compose up          # start services
    pytest tests/e2e/ -v       # run E2E tests
"""

import logging
from pathlib import Path

import pytest
from playwright.sync_api import Page

logger = logging.getLogger(__name__)

# Screenshot directory for failures
SCREENSHOT_DIR = Path(__file__).resolve().parent.parent.parent.parent / "screenshot" / "e2e-failures"


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict) -> dict:
    """Set base_url so page.goto('/v1') works without full URL."""
    return {
        **browser_context_args,
        "base_url": "http://localhost:8000",
        "viewport": {"width": 1280, "height": 900},
        "locale": "zh-CN",
    }


@pytest.fixture(autouse=True)
def check_service(page: Page) -> None:
    """Verify backend service is reachable before each test.
    Mark test as skipped (not failed) if service is down.
    """
    try:
        response = page.request.get("http://localhost:8000/v1/search?q=healthcheck")
        # Accept 200, 422, 503 — any response means the backend is up
        if response.status_code >= 500 and response.status_code != 503:
            pytest.skip(f"Backend returned {response.status_code}, check docker-compose")
    except Exception as e:
        pytest.skip(f"Cannot reach backend at http://localhost:8000: {e}")


@pytest.fixture(autouse=True)
def screenshot_on_failure(page: Page, request: pytest.FixtureRequest) -> None:
    """Automatically capture a screenshot when a test fails."""
    yield
    if hasattr(request.node, "rep_call") and request.node.rep_call.failed:
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        name = request.node.name
        path = SCREENSHOT_DIR / f"{name}.png"
        try:
            page.screenshot(path=str(path))
            logger.info(f"Failure screenshot saved: {path}")
        except Exception as exc:
            logger.warning(f"Failed to capture screenshot: {exc}")


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo) -> None:
    """Attach test result to the node for screenshot_on_failure access."""
    outcome = yield
    rep = outcome.get_result()
    setattr(item, "rep_" + rep.when, rep)
