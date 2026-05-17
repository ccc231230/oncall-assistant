import { useState, useRef, useEffect, FormEvent } from "react";
import { useConversations } from "../hooks/useConversations";
import ConversationSidebar from "../components/ConversationSidebar";
import ToolCallCard from "../components/ToolCallCard";
import FileUpload from "../components/FileUpload";
import type { Message, RenderedEvent, PendingTool, ReActTurn } from "../types";

function parseSSE(buffer: string): {
  events: Array<{ type: string; data: Record<string, unknown> }>;
  remaining: string;
} {
  const events: Array<{ type: string; data: Record<string, unknown> }> = [];
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
      events.push({ type: eventType, data: JSON.parse(dataStr) as Record<string, unknown> });
    } catch {
      /* skip malformed */
    }
  }
  return { events, remaining };
}

export default function V3Agent() {
  const {
    conversations,
    activeId,
    activeConversation,
    createConversation,
    switchConversation,
    deleteConversation,
    updateMessages,
  } = useConversations();

  const messages: Message[] = activeConversation?.messages ?? [];
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Ensure we always have an active conversation
  useEffect(() => {
    if (!activeId) {
      createConversation();
    }
  }, [activeId, createConversation]);

  async function handleSend(e: FormEvent) {
    e.preventDefault();
    if (!input.trim() || loading) return;
    if (!activeId) return;

    const userMsg: Message = { role: "user", content: input.trim() };
    const updatedMessages = [...messages, userMsg];
    setInput("");
    setLoading(true);

    // Show user message immediately
    updateMessages(updatedMessages);

    const assistantMsg: Message = {
      role: "assistant",
      content: "",
      events: [],
    };
    const messagesWithAssistant = [...updatedMessages, assistantMsg];
    updateMessages(messagesWithAssistant);

    // Track pending tool calls and turns
    let pendingTool: PendingTool | null = null;
    let currentTurn: ReActTurn | null = null;
    const turns: ReActTurn[] = [];
    let answerStarted = false;  // track streaming answer start

    function flushTurn() {
      if (currentTurn) {
        turns.push(currentTurn);
        currentTurn = null;
      }
    }

    function appendEvent(event: RenderedEvent) {
      const allMessages = [...updatedMessages, assistantMsg];
      const last = allMessages[allMessages.length - 1];
      if (last && last.role === "assistant") {
        const existing = last.events || [];
        if (event.type === "answer" && existing.length > 0 && existing[existing.length - 1].type === "answer") {
          // Merge consecutive answer chunks into one event to avoid fragmented rendering
          existing[existing.length - 1].content += event.content;
          last.events = existing;
        } else {
          last.events = [...existing, event];
        }
        last.turns = [...turns];
        if (currentTurn) {
          last.turns = [...turns, currentTurn];
        }
        if (event.type === "answer") {
          last.content = (last.content || "") + event.content;
        }
      }
      updateMessages(allMessages);
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
            case "thought": {
              flushTurn();
              currentTurn = {
                turnNumber: turns.length + 1,
                thought: (evt.data.content as string) || "",
              };
              appendEvent({
                type: "thought",
                content: currentTurn.thought,
              });
              break;
            }
            case "tool_call": {
              pendingTool = {
                tool: (evt.data.tool as string) || "unknown",
                arguments: (evt.data.arguments as Record<string, string>) || {},
              };
              if (currentTurn) {
                currentTurn.toolCall = { ...pendingTool };
              }
              break;
            }
            case "tool_result": {
              const resultContent = (evt.data.content as string) || "";
              if (pendingTool) {
                if (currentTurn) {
                  currentTurn.toolResult = resultContent;
                }
                appendEvent({
                  type: "tool",
                  content: resultContent,
                  tool: pendingTool.tool,
                  arguments: pendingTool.arguments,
                  result: resultContent,
                });
              } else {
                appendEvent({
                  type: "tool",
                  content: resultContent,
                  tool: "readFile",
                  arguments: {},
                  result: resultContent,
                });
              }
              pendingTool = null;
              break;
            }
            case "answer": {
              if (!answerStarted) {
                flushTurn();
                answerStarted = true;
              }
              const answerContent = (evt.data.content as string) || "";
              appendEvent({ type: "answer", content: answerContent });
              break;
            }
            case "error": {
              const errorContent = (evt.data.content as string) || "";
              if (currentTurn) {
                currentTurn.error = errorContent;
              }
              appendEvent({ type: "error", content: errorContent });
              break;
            }
          }
        }
      }

      // Flush any remaining turn
      flushTurn();
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
    <div className="flex h-[calc(100vh-4rem)]">
      {/* Sidebar */}
      <ConversationSidebar
        conversations={conversations}
        activeId={activeId}
        onSelect={(id) => {
          switchConversation(id);
          setSidebarOpen(false); // close on mobile after select
        }}
        onDelete={deleteConversation}
        onCreate={() => {
          createConversation();
          setSidebarOpen(false);
        }}
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
      />

      {/* Main Chat */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <div className="px-4 lg:px-6 py-4 border-b border-gray-200 bg-white">
          <h2 className="text-xl font-bold text-gray-900">Phase 3 · On-Call Agent</h2>
          <p className="text-gray-500 text-xs mt-0.5">
            基于 Kimi API 的智能 Agent，自动查阅 SOP 文档回答值班问题
          </p>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50">
          {messages.length === 0 && (
            <div className="text-center py-20 text-gray-400">
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
            <div
              key={i}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[85%] rounded-lg ${
                  msg.role === "user"
                    ? "bg-blue-600 text-white px-4 py-2"
                    : "bg-white border border-gray-200 shadow-sm"
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
                              <div
                                key={j}
                                className="text-xs text-gray-400 italic px-4 py-1 border-b border-gray-100"
                              >
                                💭 {evt.content}
                              </div>
                            );
                          case "tool":
                            return (
                              <div key={j} className="px-4 py-1 border-b border-gray-100">
                                <ToolCallCard
                                  tool={evt.tool || "unknown"}
                                  arguments={evt.arguments || {}}
                                  result={evt.result || evt.content}
                                  stepNumber={
                                    msg.events
                                      ?.filter(
                                        (e, idx) => e.type === "tool" && idx <= j
                                      ).length
                                  }
                                />
                              </div>
                            );
                          case "answer":
                            return (
                              <div
                                key={j}
                                className="px-4 py-3 text-sm text-gray-800 whitespace-pre-wrap leading-relaxed"
                              >
                                {evt.content}
                              </div>
                            );
                          case "error":
                            return (
                              <div
                                key={j}
                                className="px-4 py-2 text-sm text-red-600 bg-red-50 mx-4 my-2 rounded"
                              >
                                ❌ {evt.content}
                              </div>
                            );
                          default:
                            return null;
                        }
                      })
                    ) : msg.content ? (
                      <p className="px-4 py-3 text-sm text-gray-800 whitespace-pre-wrap leading-relaxed">
                        {msg.content}
                      </p>
                    ) : (
                      <div className="px-4 py-3 flex items-center gap-2">
                        <div className="flex gap-1">
                          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
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

        {/* File Upload */}
        <FileUpload />

        {/* Input */}
        <form
          onSubmit={handleSend}
          className="border-t border-gray-200 bg-white p-4 flex gap-3"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="描述你遇到的值班问题..."
            disabled={loading}
            className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 outline-none text-sm disabled:bg-gray-100"
          />
          <button
            type="submit"
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
