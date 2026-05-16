"""Shared fixtures for API integration tests using fastapi.testclient.TestClient."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def mock_es_client():
    """Mock ESClient — all async methods return controllable values."""
    mock = MagicMock()
    mock.es = MagicMock()
    mock.es.ping = AsyncMock(return_value=True)
    mock.create_index = AsyncMock()
    mock.index_document = AsyncMock()
    mock.index_all_from_data = AsyncMock(return_value=10)
    mock.search = AsyncMock(return_value={"query": "", "results": []})
    mock.close = AsyncMock()
    return mock


@pytest.fixture
def mock_faiss_store():
    """Mock FAISSStore — search returns empty by default."""
    mock = MagicMock()
    mock.load_model = MagicMock()
    mock.load = MagicMock(return_value=False)
    mock.build_index = MagicMock()
    mock.save = MagicMock()
    mock.search = MagicMock(return_value={"query": "", "results": []})
    return mock


@pytest.fixture
def client(mock_es_client, mock_faiss_store):
    """
    TestClient with ES and FAISS mocked at constructor level.
    The lifespan creates mocked ES/FAISS instances, so singletons are set correctly.
    Patches app.main.ESClient/FAISSStore directly to avoid module caching issues.
    """
    import app.main
    with patch.object(app.main, "ESClient", return_value=mock_es_client, create=True), \
         patch.object(app.main, "FAISSStore", return_value=mock_faiss_store, create=True):
        with TestClient(app.main.app, raise_server_exceptions=False) as c:
            yield c


@pytest.fixture
def mock_openai_client():
    """Mock AsyncOpenAI for agent chat_stream tests."""
    mock_client = MagicMock()
    mock_client.chat = MagicMock()
    mock_client.chat.completions = MagicMock()
    mock_client.chat.completions.create = AsyncMock()
    return mock_client


def parse_sse(text: str) -> list[dict]:
    """Parse SSE text into list of {type, data} dicts."""
    events = []
    for block in text.strip().split("\n\n"):
        if not block.strip():
            continue
        event_type = ""
        data_str = ""
        for line in block.split("\n"):
            if line.startswith("event: "):
                event_type = line[7:]
            elif line.startswith("data: "):
                data_str = line[6:]
        if event_type and data_str:
            import json
            try:
                events.append({"type": event_type, "data": json.loads(data_str)})
            except json.JSONDecodeError:
                events.append({"type": event_type, "data": {"raw": data_str}})
    return events
