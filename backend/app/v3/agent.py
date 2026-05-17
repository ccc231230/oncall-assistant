import json
import logging
from pathlib import Path
from typing import AsyncGenerator
from openai import AsyncOpenAI
from app.core.config import settings
from app.core.html_parser import parse_html
from app.v3.tools import read_file

logger = logging.getLogger(__name__)

# Cached SOP catalog — built once on first use to avoid re-scanning data/ on every request
_sop_catalog_cache: str | None = None


def _build_sop_catalog() -> str:
    """Scan data/ directory and build a formatted SOP catalog string."""
    global _sop_catalog_cache
    if _sop_catalog_cache is not None:
        return _sop_catalog_cache

    data_dir = Path(settings.DATA_DIR)
    if not data_dir.exists():
        _sop_catalog_cache = "(data/ 目录不存在)"
        return _sop_catalog_cache

    files = sorted(data_dir.glob("*.html"))
    if not files:
        _sop_catalog_cache = "(data/ 目录下暂无 SOP 文档)"
        return _sop_catalog_cache

    lines = [f"data/ 目录下有 {len(files)} 份 SOP 文档："]
    for f in files:
        try:
            html = f.read_text(encoding="utf-8")
            parsed = parse_html(html)
            title = parsed.get("title", "未命名")
            lines.append(f"- {f.name}：{title}")
        except Exception:
            lines.append(f"- {f.name}")

    _sop_catalog_cache = "\n".join(lines)
    logger.info(f"Built SOP catalog with {len(files)} documents")
    return _sop_catalog_cache


def _build_system_prompt() -> str:
    catalog = _build_sop_catalog()
    return f"""你是一个 On-Call 值班助手，专门帮助工程师处理线上故障。你可以使用 readFile 工具来读取部门的 SOP（标准操作流程）文档。

## 工作流程
1. 首先评估用户描述的问题是否清晰具体：
   - 如果问题描述模糊（例如只说"服务器挂了"、"服务出问题了"、"网站打不开了"），必须先追问关键信息：
     · 哪个服务 / 哪个系统出了问题？
     · 具体什么现象？（报错信息、监控指标异常、用户反馈等）
     · 什么时间开始的？影响范围有多大？
   - 不要在信息不足时盲目猜测或直接查阅文档
   - 追问时一次提出 2-3 个最关键的问题，不要一次问太多
2. 当用户提供了足够的故障信息后，根据问题类型确定需要查阅哪个 SOP 文档
3. 使用 readFile 工具读取相关的 SOP 文档（传入文件名，如 sop-001.html）
4. 根据 SOP 文档内容，给出具体的处理步骤和建议
5. 如果需要综合多个 SOP，可以多次调用 readFile

## 可用的 SOP 文档
{catalog}

## 注意事项
- 必须先阅读相关 SOP 再给出建议，不要凭空编造故障处理步骤
- 给出具体的操作步骤和命令，而非泛泛的建议
- 如果涉及 P0 级别故障（核心服务完全不可用、数据丢失、安全入侵等），提醒用户及时升级并通知相关团队
- 回答使用中文
- 每次只读取当前最相关的一两份文档，确认方向正确后再读取更多"""


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

    # Build messages list with dynamic system prompt
    messages = [{"role": "system", "content": _build_system_prompt()}]
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
                stream=True,
                stream_options={"include_usage": True},
            )

            collected_content = ""
            collected_tool_calls: dict[int, dict] = {}

            async for chunk in response:
                delta = chunk.choices[0].delta if chunk.choices else None
                if not delta:
                    continue

                # --- Accumulate text content (streaming answer) ---
                if delta.content:
                    collected_content += delta.content
                    yield _build_sse(
                        "answer",
                        {"content": delta.content},
                    )

                # --- Accumulate tool call deltas ---
                if delta.tool_calls:
                    for tc_delta in delta.tool_calls:
                        idx = tc_delta.index
                        if idx not in collected_tool_calls:
                            collected_tool_calls[idx] = {
                                "id": "",
                                "name": "",
                                "arguments": "",
                            }
                        entry = collected_tool_calls[idx]
                        if tc_delta.id:
                            entry["id"] = tc_delta.id
                        if tc_delta.function:
                            if tc_delta.function.name:
                                entry["name"] += tc_delta.function.name
                            if tc_delta.function.arguments:
                                entry["arguments"] += tc_delta.function.arguments

            # --- Chunk stream ended: decide tool_calls vs answer ---
            if collected_tool_calls:
                for tc in collected_tool_calls.values():
                    tool_name = tc["name"]
                    try:
                        tool_args = json.loads(tc["arguments"]) if tc["arguments"] else {}
                    except json.JSONDecodeError:
                        tool_args = {}

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
                            "content": result[:2000],
                        },
                    )

                    # Append tool call and result to messages
                    messages.append(
                        {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": tc["id"],
                                    "type": "function",
                                    "function": {
                                        "name": tool_name,
                                        "arguments": tc["arguments"],
                                    },
                                }
                            ],
                        }
                    )
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": result,
                        }
                    )

                continue  # Next turn

            # No tool calls — answer was already streamed via chunks
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
