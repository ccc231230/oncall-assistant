import { useState } from "react";

interface ToolCallCardProps {
  tool: string;
  arguments: Record<string, string>;
  result: string;
  stepNumber?: number;
  isStreaming?: boolean;
  elapsedMs?: number;
}

export default function ToolCallCard({
  tool,
  arguments: args,
  result,
  stepNumber,
  isStreaming,
  elapsedMs,
}: ToolCallCardProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 my-1.5">
      <div className="flex items-center gap-2 text-sm">
        {stepNumber && (
          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-blue-600 text-white">
            {stepNumber}
          </span>
        )}
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-600 text-white">
          TOOL
        </span>
        <span className="font-mono text-blue-800 font-medium">{tool}</span>
        <span className="text-gray-500 text-xs">
          ({Object.entries(args).map(([k, v]) => `${k}=${v}`).join(", ")})
        </span>
        {isStreaming ? (
          <span className="ml-auto flex items-center gap-1 text-xs text-blue-500">
            <span className="inline-block w-2 h-2 bg-blue-400 rounded-full animate-pulse" />
            执行中...
          </span>
        ) : (
          <>
            {elapsedMs != null && (
              <span className="ml-auto text-xs text-gray-400">{elapsedMs}ms</span>
            )}
            <button
              onClick={() => setExpanded(!expanded)}
              className="ml-auto text-xs text-blue-500 hover:text-blue-700 underline"
            >
              {expanded ? "收起" : "查看结果"}
            </button>
          </>
        )}
      </div>
      {expanded && !isStreaming && (
        <pre className="mt-2 text-xs text-gray-700 bg-white rounded p-2 border border-blue-100 max-h-40 overflow-auto whitespace-pre-wrap">
          {result || "(无返回内容)"}
        </pre>
      )}
    </div>
  );
}
