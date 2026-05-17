import { useState, useEffect } from "react";
import ReActTurn from "./ReActTurn";
import type { ReActTurn as ReActTurnType } from "../types";

interface ReasoningTraceProps {
  turns: ReActTurnType[];
  isComplete: boolean;
}

export default function ReasoningTrace({ turns, isComplete }: ReasoningTraceProps) {
  const [expanded, setExpanded] = useState(!isComplete);

  useEffect(() => {
    if (!isComplete) {
      setExpanded(true);
    }
  }, [isComplete]);

  if (turns.length === 0) return null;

  return (
    <div className="border-t border-gray-100">
      {/* Toggle header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-2 text-xs text-gray-500 hover:bg-gray-50 transition-colors"
      >
        <span>
          {isComplete
            ? `共 ${turns.length} 步推理 · ${expanded ? "收起" : "查看详情"}`
            : `推理中... (已完成 ${turns.length} 步)`}
        </span>
        <span className={`transform transition-transform ${expanded ? "rotate-180" : ""}`}>
          ▾
        </span>
      </button>

      {/* Turns */}
      {expanded && (
        <div className="px-4 py-2">
          {turns.map((turn, i) => (
            <ReActTurn
              key={i}
              turn={turn}
              isLast={i === turns.length - 1}
              isStreaming={!isComplete}
            />
          ))}
        </div>
      )}
    </div>
  );
}
