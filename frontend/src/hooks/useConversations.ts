import { useState, useCallback } from "react";
import type { Conversation, ConversationIndex, Message } from "../types";

const STORAGE_KEY = "oncall_v3_conversations";

function generateId(): string {
  return crypto.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function loadIndex(): ConversationIndex {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { activeId: null, conversations: [] };
    const data = JSON.parse(raw) as ConversationIndex;
    // Basic validation
    if (!Array.isArray(data.conversations)) {
      return { activeId: null, conversations: [] };
    }
    return data;
  } catch {
    return { activeId: null, conversations: [] };
  }
}

function saveIndex(index: ConversationIndex): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(index));
  } catch (e) {
    if (e instanceof DOMException && e.name === "QuotaExceededError") {
      // Prune oldest conversations to free space
      const sorted = [...index.conversations].sort(
        (a, b) => new Date(a.updatedAt).getTime() - new Date(b.updatedAt).getTime()
      );
      // Keep only the 20 most recent
      index.conversations = sorted.slice(-20);
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(index));
      } catch {
        // give up silently
      }
    }
  }
}

export function useConversations() {
  const [index, setIndex] = useState<ConversationIndex>(loadIndex);

  const conversations = index.conversations;
  const activeId = index.activeId;
  const activeConversation =
    conversations.find((c) => c.id === activeId) ?? null;

  const persist = useCallback((newIndex: ConversationIndex) => {
    setIndex(newIndex);
    saveIndex(newIndex);
  }, []);

  const createConversation = useCallback((): string => {
    const id = generateId();
    const now = new Date().toISOString();
    const conv: Conversation = {
      id,
      title: "新对话",
      createdAt: now,
      updatedAt: now,
      messages: [],
    };
    const newIndex: ConversationIndex = {
      activeId: id,
      conversations: [conv, ...index.conversations],
    };
    persist(newIndex);
    return id;
  }, [index, persist]);

  const switchConversation = useCallback(
    (id: string) => {
      persist({ ...index, activeId: id });
    },
    [index, persist]
  );

  const deleteConversation = useCallback(
    (id: string) => {
      const filtered = index.conversations.filter((c) => c.id !== id);
      const newActiveId = index.activeId === id ? null : index.activeId;
      persist({ activeId: newActiveId, conversations: filtered });
    },
    [index, persist]
  );

  const updateMessages = useCallback(
    (messages: Message[]) => {
      if (!activeId) return;
      const now = new Date().toISOString();
      const updated = index.conversations.map((c) => {
        if (c.id !== activeId) return c;
        const title =
          c.title === "新对话" && messages.length > 0
            ? messages[0].content.slice(0, 30) + (messages[0].content.length > 30 ? "…" : "")
            : c.title;
        return { ...c, messages, title, updatedAt: now };
      });
      persist({ ...index, conversations: updated });
    },
    [index, activeId, persist]
  );

  return {
    conversations,
    activeId,
    activeConversation,
    createConversation,
    switchConversation,
    deleteConversation,
    updateMessages,
  };
}
