"""Tests for app.v3.agent.chat_stream — mock OpenAI SDK entirely."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.v3.agent import chat_stream


# Helper to collect SSE events from the async generator
async def collect_sse(generator):
    """Consume an async SSE generator and return parsed events."""
    events = []
    async for sse_str in generator:
        for line in sse_str.strip().split("\n"):
            if line.startswith("event: "):
                event_type = line[7:]
            elif line.startswith("data: "):
                data = json.loads(line[6:])
                events.append({"type": event_type, "data": data})
    return events


def make_mock_completion(content=None, tool_calls=None):
    """Build a mock OpenAI completion response object."""
    msg = MagicMock()
    msg.content = content
    msg.tool_calls = None

    if tool_calls:
        tc_list = []
        for tc in tool_calls:
            mock_tc = MagicMock()
            mock_tc.id = tc.get("id", "call_1")
            mock_tc.function = MagicMock()
            mock_tc.function.name = tc["name"]
            mock_tc.function.arguments = json.dumps(tc.get("arguments", {}))
            tc_list.append(mock_tc)
        msg.tool_calls = tc_list

    choice = MagicMock()
    choice.message = msg

    response = MagicMock()
    response.choices = [choice]

    return response


class TestAgentNoTool:
    """Agent 无需工具调用时，直接返回答案。"""

    @pytest.mark.asyncio
    async def test_direct_answer(self):
        """mock LLM 直接返回答案时，SSE 只包含 answer 事件。"""
        mock_response = make_mock_completion(
            content="根据您的描述，建议重启服务并检查日志。"
        )

        with patch("app.v3.agent.AsyncOpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_client.chat = MagicMock()
            mock_client.chat.completions = MagicMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai_cls.return_value = mock_client

            events = await collect_sse(chat_stream("服务出了问题", []))

            # Should only have answer event (no tool calls)
            event_types = [e["type"] for e in events]
            assert "answer" in event_types
            assert "tool_call" not in event_types
            assert "tool_result" not in event_types
            assert events[-1]["type"] == "answer"
            assert "重启服务" in events[-1]["data"]["content"]


class TestAgentSingleTool:
    """Agent 单次工具调用流程。"""

    @pytest.mark.asyncio
    async def test_single_tool_call_read_file(self):
        """
        mock LLM 返回 readFile tool_call → 验证 SSE 事件顺序：
        thought → tool_call → tool_result → answer
        """
        tool_call_resp = make_mock_completion(
            content=None,
            tool_calls=[{"id": "call_1", "name": "readFile", "arguments": {"fname": "sop-001.html"}}],
        )
        final_answer = make_mock_completion(
            content="根据 SOP-001，OOM 后应立即保存堆转储文件并联系开发团队。"
        )

        with patch("app.v3.agent.AsyncOpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_client.chat = MagicMock()
            mock_client.chat.completions = MagicMock()
            mock_client.chat.completions.create = AsyncMock(
                side_effect=[tool_call_resp, final_answer]
            )
            mock_openai_cls.return_value = mock_client

            with patch("app.v3.agent.read_file", return_value="# SOP-001\n\nOOM 处理步骤..."):
                events = await collect_sse(chat_stream("服务 OOM 了怎么办", []))

            event_types = [e["type"] for e in events]
            assert event_types == ["thought", "tool_call", "tool_result", "answer"], (
                f"Expected [thought, tool_call, tool_result, answer], got {event_types}"
            )
            assert events[1]["data"]["tool"] == "readFile"
            assert events[1]["data"]["arguments"]["fname"] == "sop-001.html"
            assert "OOM" in events[3]["data"]["content"]


class TestAgentMultiTurn:
    """Agent 多轮工具调用。"""

    @pytest.mark.asyncio
    async def test_two_round_tool_calls(self):
        """mock LLM 连续两轮调用工具，验证能正确处理。"""
        tc1 = make_mock_completion(
            content=None,
            tool_calls=[{"id": "c1", "name": "readFile", "arguments": {"fname": "sop-001.html"}}],
        )
        tc2 = make_mock_completion(
            content=None,
            tool_calls=[{"id": "c2", "name": "readFile", "arguments": {"fname": "sop-004.html"}}],
        )
        final = make_mock_completion(content="综合 SOP-001 和 SOP-004，建议同时检查后端和基础设施。")

        with patch("app.v3.agent.AsyncOpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_client.chat = MagicMock()
            mock_client.chat.completions = MagicMock()
            mock_client.chat.completions.create = AsyncMock(
                side_effect=[tc1, tc2, final]
            )
            mock_openai_cls.return_value = mock_client

            with patch("app.v3.agent.read_file", return_value="SOP content..."):
                events = await collect_sse(chat_stream("P0 故障响应", []))

            event_types = [e["type"] for e in events]
            # Two thought → tool_call → tool_result cycles, then answer
            assert event_types.count("tool_call") == 2
            assert event_types.count("thought") == 2
            assert event_types[-1] == "answer"


class TestAgentToolResultTruncation:
    """工具结果截断测试。"""

    @pytest.mark.asyncio
    async def test_result_truncated_to_2000(self):
        """工具结果超过 2000 字符时被截断。"""
        long_content = "X" * 3000
        tool_resp = make_mock_completion(
            content=None,
            tool_calls=[{"id": "c1", "name": "readFile", "arguments": {"fname": "sop-005.html"}}],
        )
        final_resp = make_mock_completion(content="分析完成。")

        with patch("app.v3.agent.AsyncOpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_client.chat = MagicMock()
            mock_client.chat.completions = MagicMock()
            mock_client.chat.completions.create = AsyncMock(
                side_effect=[tool_resp, final_resp]
            )
            mock_openai_cls.return_value = mock_client

            with patch("app.v3.agent.read_file", return_value=long_content):
                events = await collect_sse(chat_stream("安全检查", []))

            tool_result_event = next(e for e in events if e["type"] == "tool_result")
            assert len(tool_result_event["data"]["content"]) <= 2000


class TestAgentErrorHandling:
    """Agent 错误处理。"""

    @pytest.mark.asyncio
    async def test_api_exception_yields_error_event(self):
        """mock API 异常时，SSE 流包含 error 事件。"""
        with patch("app.v3.agent.AsyncOpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_client.chat = MagicMock()
            mock_client.chat.completions = MagicMock()
            mock_client.chat.completions.create = AsyncMock(
                side_effect=Exception("API rate limit exceeded")
            )
            mock_openai_cls.return_value = mock_client

            events = await collect_sse(chat_stream("测试", []))

            assert len(events) == 1
            assert events[0]["type"] == "error"
            assert "rate limit" in events[0]["data"]["content"]
