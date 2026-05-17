import { Routes, Route, Navigate, NavLink } from "react-router-dom";
import V1Search from "./pages/V1Search";
import V2Search from "./pages/V2Search";
import V3Agent from "./pages/V3Agent";

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  `px-4 py-2 rounded-md text-sm font-medium transition-colors ${
    isActive
      ? "bg-blue-600 text-white"
      : "text-gray-300 hover:bg-gray-700 hover:text-white"
  }`;

export default function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navigation Bar */}
      <nav className="bg-gray-900 shadow-lg">
        <div className="max-w-6xl mx-auto px-4">
          <div className="flex items-center h-14 gap-1">
            <span data-testid="nav-brand" className="text-white font-bold text-lg mr-6">On-Call 助手</span>
            <NavLink to="/v1" data-testid="nav-phase1" className={navLinkClass}>
              Phase 1 · 关键词搜索
            </NavLink>
            <NavLink to="/v2" data-testid="nav-phase2" className={navLinkClass}>
              Phase 2 · 语义搜索
            </NavLink>
            <NavLink to="/v3" data-testid="nav-phase3" className={navLinkClass}>
              Phase 3 · Agent
            </NavLink>
          </div>
        </div>
      </nav>

      {/* Page Content */}
      <Routes>
        <Route path="/" element={<Navigate to="/v1" replace />} />
        <Route path="/v1" element={<main className="max-w-6xl mx-auto px-4 py-6"><V1Search /></main>} />
        <Route path="/v2" element={<main className="max-w-6xl mx-auto px-4 py-6"><V2Search /></main>} />
        <Route path="/v3" element={<V3Agent />} />
      </Routes>
    </div>
  );
}
