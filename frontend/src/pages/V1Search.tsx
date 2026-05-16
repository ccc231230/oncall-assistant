import { useState, FormEvent } from "react";
import SearchResult from "../components/SearchResult";

interface Result {
  id: string;
  title: string;
  snippet: string;
  score: number;
}

export default function V1Search() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Result[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [searchedQuery, setSearchedQuery] = useState("");

  async function handleSearch(e: FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError("");
    setResults([]);

    try {
      const res = await fetch(`/v1/search?q=${encodeURIComponent(query)}`);
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const data = await res.json();
      setResults(data.results || []);
      setSearchedQuery(query);
    } catch (err) {
      setError(err instanceof Error ? err.message : "搜索失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Phase 1 · 关键词搜索</h2>
        <p className="text-gray-500 text-sm">基于 Elasticsearch 全文检索，支持中文关键词匹配</p>
      </div>

      <form onSubmit={handleSearch} className="mb-6">
        <div className="flex gap-3">
          <input
            type="text"
            data-testid="search-input"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="输入搜索关键词，如 OOM、故障、CDN..."
            className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm"
          />
          <button
            type="submit"
            data-testid="search-button"
            disabled={loading}
            className="px-6 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium transition-colors"
          >
            {loading ? "搜索中..." : "搜索"}
          </button>
        </div>
      </form>

      {error && (
        <div data-testid="search-error" className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4 text-sm">
          {error}
        </div>
      )}

      {searchedQuery && !loading && (
        <p data-testid="search-result-count" className="text-sm text-gray-500 mb-4">
          搜索 "<span className="font-medium text-gray-700">{searchedQuery}</span>" 共找到{" "}
          <span className="font-medium text-gray-700">{results.length}</span> 个结果
        </p>
      )}

      <div data-testid="search-results" className="space-y-3">
        {results.map((r) => (
          <SearchResult key={r.id} {...r} scoreLabel="BM25" />
        ))}
      </div>

      {!loading && searchedQuery && results.length === 0 && (
        <div data-testid="search-empty" className="text-center py-12 text-gray-400">
          <p className="text-lg mb-2">未找到相关结果</p>
          <p className="text-sm">尝试更换搜索词</p>
        </div>
      )}

      {!searchedQuery && !loading && (
        <div data-testid="search-initial" className="text-center py-16 text-gray-400">
          <p className="text-lg mb-2">输入关键词开始搜索</p>
          <p className="text-sm">支持中英文混合搜索</p>
        </div>
      )}
    </div>
  );
}
