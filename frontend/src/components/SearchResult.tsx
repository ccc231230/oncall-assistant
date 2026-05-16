interface SearchResultProps {
  id: string;
  title: string;
  snippet: string;
  score: number;
  scoreLabel?: string;
}

export default function SearchResult({ id, title, snippet, score, scoreLabel = "相关度" }: SearchResultProps) {
  return (
    <div data-testid="result-card" className="bg-white rounded-lg border border-gray-200 p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <h3 data-testid="result-title" className="text-lg font-semibold text-gray-900 mb-1 truncate">
            {title}
          </h3>
          <p className="text-xs text-gray-400 mb-2">文档 ID: {id}</p>
          <p
            data-testid="result-snippet"
            className="text-sm text-gray-600 leading-relaxed"
            dangerouslySetInnerHTML={{ __html: snippet }}
          />
        </div>
        <div className="flex-shrink-0">
          <span data-testid="result-score" className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700">
            {scoreLabel}: {score.toFixed(2)}
          </span>
        </div>
      </div>
    </div>
  );
}
