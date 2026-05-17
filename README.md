# On-Call Assistant

基于部门 SOP 文档的智能值班助手，提供**关键词搜索**、**语义检索**和**对话式 Agent** 三个阶段递进的能力。

## 三阶段能力

| 阶段 | 路由 | 能力 | 技术 |
|------|------|------|------|
| Phase 1 | `/v1` | 关键词搜索 | Elasticsearch 8.x + smartcn 中文分词 |
| Phase 2 | `/v2` | 语义搜索 | sentence-transformers + FAISS 向量索引 |
| Phase 3 | `/v3` | 对话式 Agent | Kimi API (kimi-k2.6) + ReAct 循环 + SSE 流式输出 |

### Phase 3 特性

- **ReAct Agent 循环**：模型自主决定何时查阅 SOP 文档，工具调用过程以时间线可视化展示
- **流式输出**：最终回答逐词推送，无需等待完整生成
- **对话历史**：localStorage 持久化，支持多轮对话的创建/切换/删除
- **文件上传**：支持拖拽上传 .html SOP 文档，自动刷新文档列表
- **动态 SOP 目录**：启动时扫描 `data/` 自动生成文档索引，无需手动维护提示词
- **追问引导**：当用户问题模糊时（如"服务器挂了"），Agent 会主动追问关键信息

## 项目结构

```
oncall-assistant/
├── backend/
│   ├── app/
│   │   ├── core/           # 共享模块（配置、HTML 解析器、数据模型）
│   │   ├── v1/             # Phase 1 关键词搜索（ES 客户端 + 路由）
│   │   ├── v2/             # Phase 2 语义搜索（FAISS 存储 + 路由）
│   │   └── v3/             # Phase 3 Agent（ReAct 循环 + 工具调用 + 文件上传）
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/     # 可复用组件（ConversationSidebar、ReActTurn、FileUpload 等）
│   │   ├── hooks/          # 自定义 hooks（useConversations）
│   │   ├── pages/          # 页面组件（V1Search、V2Search、V3Agent）
│   │   ├── types.ts        # 共享 TypeScript 类型
│   │   └── App.tsx         # 路由入口
│   └── dist/               # 构建产物（由后端 SPA 路由直接托管）
├── data/                   # SOP HTML 文档（10 份示例 + 可上传扩展）
├── docker-compose.yml
└── README.md
```

## 快速启动

```bash
# 1. 设置 Kimi API Key 环境变量
export KIMI_API_KEY="sk-your-key"       # Linux/macOS
# 或将 .env 文件放在项目根目录

# 2. 一键启动（首次启动会下载模型，约需 2-5 分钟）
docker compose up -d

# 3. 访问
http://localhost:8000
```

## API 路由

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/` | SPA 入口（前端页面） |
| `GET` | `/v1/search?q=` | Phase 1 关键词检索 |
| `POST` | `/v1/documents` | 索引文档到 ES |
| `GET` | `/v2/search?q=` | Phase 2 语义检索 |
| `POST` | `/v3/chat` | Phase 3 Agent 对话 (SSE 流式) |
| `POST` | `/v3/upload` | 上传 SOP HTML 文件 |
| `GET` | `/v3/files` | 列出 data/ 目录下的文件 |

### SSE 事件类型（`/v3/chat`）

| 事件 | 说明 |
|------|------|
| `thought` | Agent 的推理思路 |
| `tool_call` | 即将调用的工具及参数 |
| `tool_result` | 工具返回结果（截断至 2000 字符） |
| `answer` | 最终回答（流式，多次推送） |
| `error` | 错误信息 |

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `KIMI_API_KEY` | Kimi API 密钥（必填） | `sk-placeholder` |
| `KIMI_BASE_URL` | Kimi API 地址 | `https://api.moonshot.cn/v1` |
| `KIMI_MODEL` | 模型名称 | `kimi-k2.6` |
| `ES_HOST` | Elasticsearch 地址 | `http://localhost:9200` |
| `DATA_DIR` | SOP 文档目录 | `./data` |
| `MAX_AGENT_TURNS` | Agent 最大工具调用轮数 | `5` |
| `MAX_UPLOAD_SIZE_MB` | 上传文件大小上限 | `10` |

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.11 + FastAPI + Uvicorn |
| 前端 | React 18 + TypeScript + Vite + Tailwind CSS |
| 搜索引擎 | Elasticsearch 8.x + smartcn 中文分词 |
| 语义搜索 | sentence-transformers (paraphrase-multilingual-MiniLM-L12-v2) + FAISS |
| Agent | Kimi API (kimi-k2.6) + OpenAI SDK 兼容模式 + SSE |
| 容器化 | Docker Compose（3 服务：backend + elasticsearch + frontend SPA 静态托管） |
