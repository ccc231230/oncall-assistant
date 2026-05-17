import { useState } from "react";
import ToolCallCard from "./ToolCallCard";
import type { ReActTurn as ReActTurnType } from "../types";

interface ReActTurnProps {
  turn: ReActTurnType;
  isLast: boolean;
  isStreaming: boolean;
}

export default function ReActTurn({ turn, isLast, isStreaming }: ReActTurnProps) {
  const [expanded, setExpanded] = useState(isStreaming);

  return (
    <div className="relative pl-8 pb-3">
      {/* Timeline line */}
      <div className="absolute left-3 top-0 bottom-0 w-0.5 bg-blue-200" />
      {/* Timeline dot */}
      <div
        className={`absolute left-[0.375rem] top-1 w-3.5 h-3.5 rounded-full border-2 border-white ${
          isStreaming && isLast ? "bg-blue-500 animate-pulse" : "bg-blue-500"
        }`}
      />

      {/* Turn header */}
      <div className="flex items-center gap-2 mb-1.5">
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-700">
          第 {turn.turnNumber} 步
        </span>
        <span className="text-xs text-gray-400 italic">{turn.thought}</span>
      </div>

      {/* Tool call */}
      {turn.toolCall && (
        <div className="ml-2">
          <ToolCallCard
            tool={turn.toolCall.tool}
            arguments={turn.toolCall.arguments}
            result={turn.toolResult || ""}
            stepNumber={turn.turnNumber}
            isStreaming={isStreaming && isLast && !turn.toolResult}
          />
        </div>
      )}

      {/* Result preview (if not showing ToolCallCard) */}
      {turn.toolResult && !turn.toolCall && (
        <div className="ml-2">
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-xs text-blue-500 hover:text-blue-700 underline"
          >
            {expanded ? "收起结果" : "查看结果"}
          </button>
          {expanded && (
            <pre className="mt-1 text-xs text-gray-700 bg-gray-50 rounded p-2 border border-blue-100 max-h-40 overflow-auto whitespace-pre-wrap">
              {turn.toolResult}
            </pre>
          )}
        </div>
      )}

      {/* Error */}
      {turn.error && (
        <div className="ml-2 text-xs text-red-600 bg-red-50 rounded p-2 mt-1">
          {turn.error}
        </div>
      )}

      {/* Answer (for final turn) */}
      {turn.answer && (
        <div className="ml-2 mt-2 text-sm text-gray-800 whitespace-pre-wrap leading-relaxed bg-white rounded-lg border border-gray-100 p-3">
          {turn.answer}
        </div>
      )}
    </div>
  );
}
