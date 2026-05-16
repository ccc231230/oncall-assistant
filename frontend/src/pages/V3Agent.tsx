import { useState, useRef, useEffect, FormEvent } from "react";
import ToolCallCard from "../components/ToolCallCard";

interface PendingTool {
  tool: string;
  arguments: Record<string, string>;
}

interface RenderedEvent {
  type: "thought" | "tool" | "answer" | "error";
  content: string;
  tool?: string;
  arguments?: Record<string, string>;
  result?: string;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  events?: RenderedEvent[];
}

export default function V3Agent() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function parseSSE(buffer: string): { events: Array<{ type: string; data: any }>; remaining: string } {
    const events: Array<{ type: string; data: any }> = [];
    const parts = buffer.split("\n\n");
    const remaining = parts.pop() || "";

    for (const part of parts) {
      if (!part.trim()) continue;
      let eventType = "";
      let dataStr = "";
      for (const line of part.split("\n")) {
        if (line.startsWith("event: ")) eventType = line.slice(7).trim();
        else if (line.startsWith("data: ")) dataStr = line.slice(6).trim();
      }
      if (!eventType || !dataStr) continue;
      try {
        events.push({ type: eventType, data: JSON.parse(dataStr) });
      } catch { /* skip malformed */ }
    }
    return { events, remaining };
  }

  async function handleSend(e: FormEvent) {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMsg: Message = { role: "user", content: input.trim() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    const assistantMsg: Message = { role: "assistant", content: "", events: [] };
    setMessages((prev) => [...prev, assistantMsg]);

    // Track pending tool calls to merge with their results
    let pendingTool: PendingTool | null = null;

    function appendEvent(event: RenderedEvent) {
      setMessages((prev) => {
        const updated = [...prev];
        const last = updated[updated.length - 1];
        if (last && last.role === "assistant") {
          last.events = [...(last.events || []), event];
          if (event.type === "answer") last.content = event.content;
        }
        return updated;
      });
    }

    try {
      const history = messages.map((m) => ({ role: m.role, content: m.content }));
      const res = await fetch("/v3/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMsg.content, history }),
      });

      if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const { events, remaining } = parseSSE(buffer);
        buffer = remaining;

        for (const evt of events) {
          switch (evt.type) {
            case "thought":
              appendEvent({ type: "thought", content: evt.data.content || "" });
              break;
            case "tool_call":
              pendingTool = {
                tool: evt.data.tool || "unknown",
                arguments: evt.data.arguments || {},
              };
              break;
            case "tool_result":
              if (pendingTool) {
                appendEvent({
                  type: "tool",
                  content: evt.data.content || "",
                  tool: pendingTool.tool,
                  arguments: pendingTool.arguments,
                  result: evt.data.content || "",
                });
              } else {
                appendEvent({
                  type: "tool",
                  content: evt.data.content || "",
                  tool: "readFile",
                  arguments: {},
                  result: evt.data.content || "",
                });
              }
              pendingTool = null;
              break;
            case "answer":
              appendEvent({ type: "answer", content: evt.data.content || "" });
              break;
            case "error":
              appendEvent({ type: "error", content: evt.data.content || "" });
              break;
          }
        }
      }
    } catch (err) {
      appendEvent({
        type: "error",
        content: `出错: ${err instanceof Error ? err.message : "未知错误"}`,
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Phase 3 · On-Call Agent</h2>
        <p className="text-gray-500 text-sm">
          基于 Kimi API (kimi-k2.6) 的智能 Agent，可自动查阅 SOP 文档回答值班问题
        </p>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
        <div data-testid="chat-messages" className="h-[500px] overflow-y-auto p-4 space-y-4">
          {messages.length === 0 && (
            <div data-testid="chat-welcome" className="text-center py-20 text-gray-400">
              <p className="text-lg mb-2">On-Call 值班助手</p>
              <p className="text-sm">请描述你遇到的值班问题，我将查阅 SOP 文档为你解答</p>
              <div className="mt-4 text-xs text-gray-300 space-y-1">
                <p>试试这些问题：</p>
                <p>"服务 OOM 了怎么办？"</p>
                <p>"数据库主从延迟超过30秒怎么处理？"</p>
                <p>"怀疑有人入侵了系统"</p>
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <div key={i} data-testid={msg.role === "user" ? "user-message" : "assistant-message"} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              <div
                className={`max-w-[85%] rounded-lg ${
                  msg.role === "user"
                    ? "bg-blue-600 text-white px-4 py-2"
                    : "bg-gray-50 border border-gray-200"
                }`}
              >
                {msg.role === "user" ? (
                  <p className="text-sm">{msg.content}</p>
                ) : (
                  <div>
                    {msg.events && msg.events.length > 0 ? (
                      msg.events.map((evt, j) => {
                        switch (evt.type) {
                          case "thought":
                            return (
                              <div key={j} data-testid="thought-card" className="text-xs text-gray-400 italic px-4 py-1">
                                {evt.content}
                              </div>
                            );
                          case "tool":
                            return (
                              <div key={j} data-testid="tool-card" className="px-4 py-1">
                                <ToolCallCard
                                  tool={evt.tool || "unknown"}
                                  arguments={evt.arguments || {}}
                                  result={evt.result || evt.content}
                                />
                              </div>
                            );
                          case "answer":
                            return (
                              <div key={j} data-testid="answer-bubble" className="px-4 py-2 text-sm text-gray-800 whitespace-pre-wrap">
                                {evt.content}
                              </div>
                            );
                          case "error":
                            return (
                              <div key={j} data-testid="error-card" className="px-4 py-2 text-sm text-red-600 bg-red-50 mx-4 rounded">
                                {evt.content}
                              </div>
                            );
                          default:
                            return null;
                        }
                      })
                    ) : msg.content ? (
                      <p className="px-4 py-2 text-sm text-gray-800 whitespace-pre-wrap">
                        {msg.content}
                      </p>
                    ) : (
                      <div data-testid="loading-indicator" className="px-4 py-3 flex items-center gap-2">
                        <div className="flex gap-1">
                          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                        </div>
                        <span className="text-xs text-gray-400">思考中...</span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
          <div ref={chatEndRef} />
        </div>

        <form onSubmit={handleSend} className="border-t border-gray-200 p-4 flex gap-3">
          <input
            type="text"
            data-testid="chat-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="描述你遇到的值班问题..."
            disabled={loading}
            className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 outline-none text-sm disabled:bg-gray-100"
          />
          <button
            type="submit"
            data-testid="chat-send"
            disabled={loading || !input.trim()}
            className="px-6 py-2.5 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium transition-colors"
          >
            {loading ? "思考中..." : "发送"}
          </button>
        </form>
      </div>
    </div>
  );
}
