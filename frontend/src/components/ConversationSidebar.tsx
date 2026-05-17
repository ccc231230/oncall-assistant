import type { Conversation } from "../types";

interface ConversationSidebarProps {
  conversations: Conversation[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
  onCreate: () => void;
  isOpen: boolean;
  onToggle: () => void;
}

export default function ConversationSidebar({
  conversations,
  activeId,
  onSelect,
  onDelete,
  onCreate,
  isOpen,
  onToggle,
}: ConversationSidebarProps) {
  return (
    <>
      {/* Mobile toggle */}
      <button
        onClick={onToggle}
        className="fixed top-4 left-4 z-50 lg:hidden bg-gray-900 text-white p-2 rounded-md shadow-lg"
        aria-label="切换对话列表"
      >
        {isOpen ? "✕" : "☰"}
      </button>

      {/* Sidebar */}
      <aside
        className={`${
          isOpen ? "translate-x-0" : "-translate-x-full"
        } fixed lg:static lg:translate-x-0 z-40 top-0 left-0 h-full w-64 bg-gray-900 text-gray-200 flex flex-col transition-transform duration-200 shadow-xl`}
      >
        {/* Header */}
        <div className="p-4 border-b border-gray-700 flex items-center justify-between">
          <span className="text-white font-bold text-sm">对话历史</span>
          <button
            onClick={onCreate}
            className="text-xs bg-green-600 hover:bg-green-700 text-white px-2.5 py-1 rounded transition-colors"
          >
            + 新对话
          </button>
        </div>

        {/* List */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {conversations.length === 0 ? (
            <p className="text-xs text-gray-500 text-center py-8">暂无历史对话</p>
          ) : (
            conversations.map((conv) => (
              <div
                key={conv.id}
                onClick={() => onSelect(conv.id)}
                className={`group flex items-center gap-2 px-3 py-2 rounded-md cursor-pointer text-sm transition-colors ${
                  conv.id === activeId
                    ? "bg-gray-700 text-white"
                    : "text-gray-400 hover:bg-gray-800 hover:text-gray-200"
                }`}
              >
                <div className="flex-1 min-w-0">
                  <div className="truncate text-xs font-medium">{conv.title}</div>
                  <div className="text-xs text-gray-500 mt-0.5">
                    {conv.messages.length} 条消息 ·{" "}
                    {new Date(conv.updatedAt).toLocaleDateString("zh-CN")}
                  </div>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    if (confirm(`确定删除对话 "${conv.title}" 吗？`)) {
                      onDelete(conv.id);
                    }
                  }}
                  className="opacity-0 group-hover:opacity-100 text-gray-500 hover:text-red-400 text-xs transition-opacity"
                  title="删除对话"
                >
                  删除
                </button>
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="p-3 border-t border-gray-700 text-xs text-gray-500 text-center">
          对话记录保存在本地浏览器
        </div>
      </aside>

      {/* Overlay for mobile */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/30 z-30 lg:hidden"
          onClick={onToggle}
        />
      )}
    </>
  );
}
