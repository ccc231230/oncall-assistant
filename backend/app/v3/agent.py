import json
import logging
from typing import AsyncGenerator
from openai import AsyncOpenAI
from app.core.config import settings
from app.v3.tools import read_file

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一个 On-Call 值班助手，专门帮助工程师处理线上故障。你可以使用 readFile 工具来读取部门的 SOP（标准操作流程）文档。

## 工作流程
1. 分析用户的问题，确定需要查阅哪个 SOP 文档
2. 使用 readFile 工具读取相关的 SOP 文档（文件名如 sop-001.html, sop-002.html 等）
3. 根据 SOP 文档内容，给出具体的处理步骤和建议
4. 如果需要综合多个 SOP，可以多次调用 readFile

## 可用的 SOP 文档
data/ 目录下有 10 份 SOP 文档：
- sop-001.html：后端服务 On-Call SOP（OOM排查、服务超时、降级策略）
- sop-002.html：数据库DBA On-Call SOP（主从延迟、慢查询、连接池）
- sop-003.html：前端Web On-Call SOP（白屏、CDN、兼容性）
- sop-004.html：SRE基础设施 On-Call SOP（K8s、监控告警、容量规划）
- sop-005.html：信息安全 On-Call SOP（入侵检测、漏洞响应、DDoS）
- sop-006.html：数据平台 On-Call SOP（数据管道、ETL、Spark）
- sop-007.html：移动端 On-Call SOP（崩溃率、热修复、推送）
- sop-008.html：AI与算法 On-Call SOP（模型推理、推荐质量、GPU）
- sop-009.html：QA质量 On-Call SOP（测试环境、自动化测试、发版）
- sop-010.html：网络与CDN On-Call SOP（CDN节点、DNS、DDoS防护）

## 注意事项
- 必须先阅读相关 SOP 再给出建议，不要凭空编造
- 给出具体的操作步骤和命令
- 如果涉及 P0 级别故障，提醒用户及时升级
- 回答使用中文"""

READ_FILE_TOOL = {
    "type": "function",
    "function": {
        "name": "readFile",
        "description": "读取 data/ 目录下的 SOP HTML 文档，获取完整内容",
        "parameters": {
            "type": "object",
            "properties": {
                "fname": {
                    "type": "string",
                    "description": "要读取的文件名，例如 sop-001.html, sop-002.html",
                }
            },
            "required": ["fname"],
        },
    },
}


def _build_sse(event: str, data: dict) -> str:
    """Build an SSE-formatted string."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def chat_stream(message: str, history: list[dict]) -> AsyncGenerator[str, None]:
    """
    ReAct agent loop with SSE streaming.
    Yields SSE events: thought, tool_call, tool_result, answer, error.
    """
    client = AsyncOpenAI(
        api_key=settings.KIMI_API_KEY,
        base_url=settings.KIMI_BASE_URL,
    )

    # Build messages list
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for h in history:
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": message})

    for turn in range(settings.MAX_AGENT_TURNS):
        try:
            response = await client.chat.completions.create(
                model=settings.KIMI_MODEL,
                messages=messages,
                tools=[READ_FILE_TOOL],
                tool_choice="auto",
                temperature=0.6,
                extra_body={"thinking": {"type": "disabled"}},
            )

            choice = response.choices[0]
            msg = choice.message

            # Check for tool calls
            if msg.tool_calls:
                for tool_call in msg.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)

                    # Yield thought event
                    yield _build_sse(
                        "thought",
                        {
                            "content": f"正在查阅 SOP 文档...",
                            "turn": turn + 1,
                        },
                    )

                    # Yield tool_call event
                    yield _build_sse(
                        "tool_call",
                        {
                            "tool": tool_name,
                            "arguments": tool_args,
                        },
                    )

                    # Execute tool
                    if tool_name == "readFile":
                        result = read_file(tool_args.get("fname", ""))
                    else:
                        result = f"Error: unknown tool '{tool_name}'"

                    # Yield tool_result event
                    yield _build_sse(
                        "tool_result",
                        {
                            "content": result[:2000],  # Limit result length
                        },
                    )

                    # Append tool call and result to messages
                    messages.append(
                        {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": tool_call.id,
                                    "type": "function",
                                    "function": {
                                        "name": tool_name,
                                        "arguments": tool_call.function.arguments,
                                    },
                                }
                            ],
                        }
                    )
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": result,
                        }
                    )

                # Continue loop to get next response
                continue

            # No tool calls - final answer
            content = msg.content or ""
            yield _build_sse(
                "answer",
                {
                    "content": content,
                },
            )
            return

        except Exception as e:
            logger.error(f"Agent error on turn {turn}: {e}")
            yield _build_sse(
                "error",
                {
                    "content": f"Agent 调用出错: {str(e)}",
                },
            )
            return

    # Max turns exceeded
    yield _build_sse(
        "error",
        {
            "content": "已达到最大工具调用次数，请尝试更具体地描述您的问题。",
        },
    )
