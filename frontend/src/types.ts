/** SSE 解析出的事件 */
export interface SSEEvent {
  type: string;
  data: Record<string, unknown>;
}

/** 待合并的 pending tool 调用 */
export interface PendingTool {
  tool: string;
  arguments: Record<string, string>;
}

/** 渲染用事件（扁平化后的结果） */
export interface RenderedEvent {
  type: "thought" | "tool" | "answer" | "error";
  content: string;
  tool?: string;
  arguments?: Record<string, string>;
  result?: string;
}

/** ReAct 循环的一个回合 */
export interface ReActTurn {
  turnNumber: number;
  thought: string;
  toolCall?: { tool: string; arguments: Record<string, string> };
  toolResult?: string;
  answer?: string;
  error?: string;
}

/** 聊天消息 */
export interface Message {
  role: "user" | "assistant";
  content: string;
  events?: RenderedEvent[];
  turns?: ReActTurn[]; // Phase 3b 使用
}

/** 对话 */
export interface Conversation {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messages: Message[];
}

/** localStorage 根结构 */
export interface ConversationIndex {
  activeId: string | null;
  conversations: Conversation[];
}

/** 文件信息 */
export interface FileInfo {
  name: string;
  size: number;
  modified: string;
}

/** 上传响应 */
export interface UploadResponse {
  success: boolean;
  filename?: string;
  size?: number;
  error?: string;
}
