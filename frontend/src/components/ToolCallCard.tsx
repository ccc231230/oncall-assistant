import { useState } from "react";

interface ToolCallCardProps {
  tool: string;
  arguments: Record<string, string>;
  result: string;
}

export default function ToolCallCard({ tool, arguments: args, result }: ToolCallCardProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div data-testid="toolcall-card" className="bg-blue-50 border border-blue-200 rounded-lg p-3 my-2">
      <div className="flex items-center gap-2 text-sm">
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-600 text-white">
          TOOL
        </span>
        <span data-testid="toolcall-name" className="font-mono text-blue-800 font-medium">{tool}</span>
        <span data-testid="toolcall-args" className="text-gray-500">
          ({Object.entries(args).map(([k, v]) => `${k}=${v}`).join(", ")})
        </span>
        <button
          data-testid="toolcall-expand"
          onClick={() => setExpanded(!expanded)}
          className="ml-auto text-xs text-blue-500 hover:text-blue-700 underline"
        >
          {expanded ? "收起" : "查看结果"}
        </button>
      </div>
      {expanded && (
        <pre data-testid="toolcall-result" className="mt-2 text-xs text-gray-700 bg-white rounded p-2 border border-blue-100 max-h-40 overflow-auto whitespace-pre-wrap">
          {result}
        </pre>
      )}
    </div>
  );
}
