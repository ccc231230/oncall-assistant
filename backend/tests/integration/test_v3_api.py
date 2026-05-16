"""
Phase 3 API 集成测试 — POST /v3/chat SSE 流式 Agent 接口。

mock app.v3.agent.AsyncOpenAI，验证 SSE 事件顺序、内容、多轮工具调用和历史传递。
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

from tests.integration.conftest import parse_sse


def make_tool_call_msg(tool_calls):
    """构建模拟的 OpenAI tool_calls 响应对象。"""
    msg = MagicMock()
    msg.content = None
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

    resp = MagicMock()
    resp.choices = [choice]
    return resp


def make_answer_msg(content):
    """构建模拟的 OpenAI 直接回答响应对象。"""
    msg = MagicMock()
    msg.content = content
    msg.tool_calls = None

    choice = MagicMock()
    choice.message = msg

    resp = MagicMock()
    resp.choices = [choice]
    return resp


class TestV3ChatSSE:
    """POST /v3/chat — SSE 流式对话接口。"""

    def test_sse_content_type(self, client, mock_openai_client):
        """验证响应 Content-Type 为 text/event-stream。"""
        mock_openai_client.chat.completions.create.return_value = make_answer_msg(
            "请重启服务并检查日志。"
        )

        with patch("app.v3.agent.AsyncOpenAI", return_value=mock_openai_client), \
             patch("app.v3.agent.read_file", return_value="# SOP Content"):
            response = client.post(
                "/v3/chat",
                json={"message": "服务挂了", "history": []},
            )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

    def test_chat_direct_answer(self, client, mock_openai_client):
        """无需工具时，SSE 只包含 answer 事件。"""
        mock_openai_client.chat.completions.create.return_value = make_answer_msg(
            "请检查近期是否有代码变更或配置修改。"
        )

        with patch("app.v3.agent.AsyncOpenAI", return_value=mock_openai_client):
            response = client.post(
                "/v3/chat",
                json={"message": "数据库连接失败", "history": []},
            )

        events = parse_sse(response.text)
        event_types = [e["type"] for e in events]

        # Should only have answer event
        assert "answer" in event_types
        assert "tool_call" not in event_types

    def test_chat_OOM_workflow(self, client, mock_openai_client):
        """
        搜索 "服务 OOM" → Agent 调用 readFile(sop-001.html)。
        验证 SSE 事件顺序：thought → tool_call → tool_result → answer。
        """
        mock_openai_client.chat.completions.create.side_effect = [
            make_tool_call_msg(
                [{"id": "c1", "name": "readFile", "arguments": {"fname": "sop-001.html"}}]
            ),
            make_answer_msg("根据 SOP-001，OOM 后应立即保存堆转储并回滚到上一个稳定版本。"),
        ]

        with patch("app.v3.agent.AsyncOpenAI", return_value=mock_openai_client), \
             patch("app.v3.agent.read_file", return_value="# 后端服务 On-Call SOP\n\n处理步骤..."):
            response = client.post(
                "/v3/chat",
                json={"message": "服务 OOM 了怎么办", "history": []},
            )

        events = parse_sse(response.text)
        event_types = [e["type"] for e in events]

        assert event_types == ["thought", "tool_call", "tool_result", "answer"], \
            f"Expected [thought, tool_call, tool_result, answer], got {event_types}"

        # Verify tool_call arguments
        assert events[1]["data"]["tool"] == "readFile"
        assert events[1]["data"]["arguments"]["fname"] == "sop-001.html"

        # Verify final answer
        assert "SOP-001" in events[3]["data"]["content"]
        assert "堆转储" in events[3]["data"]["content"]

    def test_chat_intrusion_workflow(self, client, mock_openai_client):
        """
        "怀疑有人入侵了系统" → Agent 读取 sop-005.html。
        验证工具调用指向正确的安全 SOP。
        """
        mock_openai_client.chat.completions.create.side_effect = [
            make_tool_call_msg(
                [{"id": "c1", "name": "readFile", "arguments": {"fname": "sop-005.html"}}]
            ),
            make_answer_msg("根据 SOP-005，首先确认入侵类型并立即升级到安全团队负责人。"),
        ]

        with patch("app.v3.agent.AsyncOpenAI", return_value=mock_openai_client), \
             patch("app.v3.agent.read_file", return_value="# 信息安全 On-Call SOP\n\n安全事件响应流程..."):
            response = client.post(
                "/v3/chat",
                json={"message": "怀疑有人入侵了系统", "history": []},
            )

        events = parse_sse(response.text)
        event_types = [e["type"] for e in events]

        assert "tool_call" in event_types
        tc_event = next(e for e in events if e["type"] == "tool_call")
        assert tc_event["data"]["arguments"]["fname"] == "sop-005.html"

        assert "answer" in event_types
        answer_event = next(e for e in events if e["type"] == "answer")
        assert "SOP-005" in answer_event["data"]["content"]

    def test_chat_multi_turn(self, client, mock_openai_client):
        """Agent 连续两轮调用 readFile，然后给出综合回答。"""
        mock_openai_client.chat.completions.create.side_effect = [
            make_tool_call_msg(
                [{"id": "c1", "name": "readFile", "arguments": {"fname": "sop-001.html"}}]
            ),
            make_tool_call_msg(
                [{"id": "c2", "name": "readFile", "arguments": {"fname": "sop-004.html"}}]
            ),
            make_answer_msg("综合 SOP-001 和 SOP-004，建议同时排查后端服务和基础设施。"),
        ]

        with patch("app.v3.agent.AsyncOpenAI", return_value=mock_openai_client), \
             patch("app.v3.agent.read_file", return_value="# SOP Content"):
            response = client.post(
                "/v3/chat",
                json={"message": "P0 故障响应流程", "history": []},
            )

        events = parse_sse(response.text)
        event_types = [e["type"] for e in events]

        # Two thought → tool_call → tool_result cycles
        assert event_types.count("tool_call") == 2
        assert event_types.count("thought") == 2
        assert event_types.count("tool_result") == 2
        assert event_types[-1] == "answer"

    def test_chat_history_persistence(self, client, mock_openai_client):
        """
        传入 history，验证 history 被正确拼接到 messages。
        通过检查 chat.completions.create 的调用参数来验证。
        """
        mock_openai_client.chat.completions.create.return_value = make_answer_msg(
            "已根据历史上下文回答。"
        )

        with patch("app.v3.agent.AsyncOpenAI", return_value=mock_openai_client):
            response = client.post(
                "/v3/chat",
                json={
                    "message": "还有其他问题吗？",
                    "history": [
                        {"role": "user", "content": "服务 OOM 了怎么办"},
                        {"role": "assistant", "content": "请检查 JVM 内存设置。"},
                    ],
                },
            )

        assert response.status_code == 200

        # Verify the messages passed to the API include history
        call_args = mock_openai_client.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]

        # messages = [system, history[0], history[1], user_current]
        assert len(messages) == 4
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "服务 OOM 了怎么办"
        assert messages[2]["role"] == "assistant"
        assert messages[2]["content"] == "请检查 JVM 内存设置。"
        assert messages[3]["role"] == "user"
        assert messages[3]["content"] == "还有其他问题吗？"
