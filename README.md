# On-Call 助手

基于部门 SOP 文档的智能值班助手 Web 应用，提供关键词检索、语义搜索和对话式 Agent 三种能力。

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.11 + FastAPI + Uvicorn |
| 前端 | React 18 + TypeScript + Vite + Tailwind CSS |
| 搜索引擎 | Elasticsearch 8.x + smartcn 中文分词 |
| 语义搜索 | sentence-transformers + FAISS |
| Agent | Kimi API (kimi-k2.6) + OpenAI SDK 兼容模式 |

## 启动命令

```bash
# 一键启动（需要 Docker 环境）
docker-compose up

# 访问
http://localhost:8000
```

## API 路由

| 路由 | 说明 |
|------|------|
| `GET /v1` | Phase 1 关键词搜索页面 |
| `POST /v1/documents` | 索引文档 |
| `GET /v1/search?q=` | 关键词检索 |
| `GET /v2` | Phase 2 语义搜索页面 |
| `GET /v2/search?q=` | 语义检索 |
| `GET /v3` | Phase 3 Agent 对话页面 |
| `POST /v3/chat` | Agent 对话 (SSE) |

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `ES_HOST` | Elasticsearch 地址 | `http://localhost:9200` |
| `KIMI_API_KEY` | Kimi API 密钥 | 占位符 |
| `DATA_DIR` | SOP HTML 文档目录 | `./data` |

---

> **请将个人简历 PDF 放入此目录**
