# On-Call Assistant · On-Call 助手

基于部门 SOP 文档的智能值班助手 — **编程面试题目一**

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat&logo=react)](https://react.dev/)
[![Elasticsearch](https://img.shields.io/badge/Elasticsearch-8.11-FEC514?style=flat&logo=elasticsearch)](https://www.elastic.co/)
[![FAISS](https://img.shields.io/badge/FAISS-cpu-blue?style=flat)](https://github.com/facebookresearch/faiss)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat&logo=docker)](https://docs.docker.com/compose/)

---

## 项目概述

On-Call 助手是一个 Web 应用，帮助值班工程师通过对话式交互快速查阅部门 SOP 文档，获取故障处理指导。采用**三阶段递进架构**，从关键词检索到语义搜索再到智能 Agent 对话，逐步增强检索与问答能力。

三种查询方式对应独立的 API 路由和前端页面，均可独立运行和测试：

| 阶段 | 路由 | 检索方式 | 核心能力 |
|------|------|----------|----------|
| Phase 1 | `/v1` | 关键词匹配 | Elasticsearch TF-IDF + smartcn 中文分词 |
| Phase 2 | `/v2` | 语义向量 | sentence-transformers + FAISS 内积搜索 |
| Phase 3 | `/v3` | Agent 对话 | ReAct 循环 + SSE 流式输出，自动查阅 SOP |

数据来源为 `data/` 目录下的 10 份 HTML 格式 SOP 文档，覆盖后端、数据库、前端、SRE、安全等十个方向的常见故障场景。

> **开发声明**：本项目在开发过程中使用了 AI 编程辅助工具（Claude Code），用于代码生成、调试和重构。所有 AI 生成的代码均经过人工审查和测试验证。

---

## 技术架构

```
┌─────────────────────────────────────────────────────────┐
│                    前端 React SPA                        │
│              React 18 + TypeScript + Tailwind            │
│            (Vite 开发 / 构建产物由 FastAPI 托管)           │
└─────────────────────┬───────────────────────────────────┘
                      │  HTTP / SSE
                      ▼
┌─────────────────────────────────────────────────────────┐
│                   后端 FastAPI                           │
│                  Python 3.11 + Uvicorn                   │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │  Phase 1 │  │   Phase 2    │  │     Phase 3       │  │
│  │ /v1/*    │  │   /v2/*      │  │     /v3/*         │  │
│  │ ES 客户端 │  │  FAISS 存储  │  │  ReAct Agent 循环  │  │
│  └────┬─────┘  └──────┬───────┘  └─────────┬─────────┘  │
└───────┼─────────────────┼───────────────────┼───────────┘
        │                 │                   │
        ▼                 ▼                   ▼
┌───────────────┐ ┌──────────────┐ ┌─────────────────────┐
│ Elasticsearch │ │ FAISS 向量库  │ │  Kimi API (k2.6)    │
│   + smartcn   │ │ (IndexFlatIP) │ │  OpenAI SDK 兼容     │
└───────────────┘ └──────────────┘ └─────────────────────┘
```

### 三阶段技术选型

| Phase | 检索方式 | 核心技术 | 模型/引擎 |
|-------|----------|----------|-----------|
| Phase 1 | 关键词搜索 | Elasticsearch + smartcn 分词 | ES 8.x match 查询 |
| Phase 2 | 语义搜索 | sentence-transformers + FAISS | paraphrase-multilingual-MiniLM-L12-v2 (384d) |
| Phase 3 | Agent 对话 | ReAct 循环 + SSE 流式 | Kimi kimi-k2.6 (OpenAI SDK 兼容) |

### 数据流

1. **文档索引**：`data/*.html` → HTML 解析器（去除 script/style）→ 提取标题/正文 → 分别写入 ES 和 FAISS
2. **Phase 1 查询**：用户输入 → ES `match` 查询 → 返回 `id + title + snippet + score`
3. **Phase 2 查询**：用户输入 → sentence-transformers 嵌入 → FAISS 内积搜索 → 返回 top-k
4. **Phase 3 对话**：用户问题 → System Prompt → ReAct 循环（思考→工具调用→观察→回答）→ SSE 流式输出

---

## 目录结构

```
oncall-assistant/
│
├── backend/                        # Python FastAPI 后端
│   ├── app/
│   │   ├── core/                   # 共享模块
│   │   │   ├── config.py           #   配置管理（Pydantic Settings）
│   │   │   ├── html_parser.py      #   SOP HTML 解析器
│   │   │   └── models.py           #   Pydantic 数据模型
│   │   ├── v1/                     # Phase 1 – 关键词搜索
│   │   │   ├── es_client.py        #   Elasticsearch 异步客户端
│   │   │   └── router.py           #   /v1 路由
│   │   ├── v2/                     # Phase 2 – 语义搜索
│   │   │   ├── faiss_store.py      #   FAISS 向量存储
│   │   │   └── router.py           #   /v2 路由
│   │   ├── v3/                     # Phase 3 – Agent 对话
│   │   │   ├── agent.py            #   ReAct 循环 + SSE 流式
│   │   │   ├── tools.py            #   工具函数（readFile、文件上传）
│   │   │   └── router.py           #   /v3 路由
│   │   └── main.py                 # FastAPI 应用入口 + SPA 托管
│   ├── tests/
│   │   ├── e2e/                    # 端到端测试
│   │   ├── integration/            # 集成测试
│   │   └── test_*.py               # 单元测试
│   ├── Dockerfile
│   ├── requirements.txt
│   └── start.sh
│
├── frontend/                       # React TypeScript 前端
│   ├── src/
│   │   ├── components/             # 可复用组件
│   │   │   ├── ConversationSidebar.tsx  # 对话侧边栏
│   │   │   ├── FileUpload.tsx      #   拖拽文件上传
│   │   │   ├── ReActTurn.tsx       #   ReAct 回合时间线
│   │   │   ├── ReasoningTrace.tsx  #   推理追踪折叠面板
│   │   │   ├── ToolCallCard.tsx    #   工具调用卡片
│   │   │   └── SearchResult.tsx    #   搜索结果项
│   │   ├── hooks/
│   │   │   └── useConversations.ts #   localStorage 对话管理
│   │   ├── pages/
│   │   │   ├── V1Search.tsx        #   Phase 1 搜索页
│   │   │   ├── V2Search.tsx        #   Phase 2 搜索页
│   │   │   └── V3Agent.tsx         #   Phase 3 Agent 对话页
│   │   ├── types.ts                #  共享 TypeScript 类型
│   │   └── App.tsx                 #  路由入口
│   ├── dist/                       # 构建产物（FastAPI 托管）
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.js
│
├── data/                           # SOP HTML 文档（10 份）
│   ├── sop-001.html                #   后端服务 On-Call SOP
│   ├── sop-002.html                #   数据库 DBA On-Call SOP
│   ├── sop-003.html                #   前端 Web On-Call SOP
│   ├── sop-004.html                #   SRE 基础设施 On-Call SOP
│   ├── sop-005.html                #   信息安全 On-Call SOP
│   ├── sop-006.html                #   数据平台 On-Call SOP
│   ├── sop-007.html                #   移动端 On-Call SOP
│   ├── sop-008.html                #   AI 与算法 On-Call SOP
│   ├── sop-009.html                #   QA 质量 On-Call SOP
│   └── sop-010.html                #   网络与 CDN On-Call SOP
│
├── docker-compose.yml              # Docker 编排
├── Dockerfile.es                   # ES 镜像（含 smartcn 插件）
└── README.md
```

---

## 快速启动

### 前置要求

| 依赖 | 版本要求 | 说明 |
|------|----------|------|
| Docker + Docker Compose | 最新稳定版 | 运行 Elasticsearch 和完整部署 |
| Python | 3.11+ | 后端开发（本地方式） |
| Node.js / npm | 18+ / 9+ | 前端开发（本地方式） |
| Kimi API Key | — | Phase 3 需要，从 [Moonshot 开放平台](https://platform.moonshot.cn/) 获取 |

### 方式一：Docker 完整部署（推荐）

```bash
# 1. 克隆项目
git clone <repo-url>
cd oncall-assistant

# 2. 设置 Kimi API Key（创建 .env 文件或直接 export）
echo 'KIMI_API_KEY=sk-your-key-here' > .env

# 3. 一键启动（首次需下载模型和构建镜像，约 3-5 分钟）
docker compose up -d

# 4. 等待服务就绪后验证
curl http://localhost:8000/docs        # API 文档页面
curl http://localhost:8000/v3/files    # 查看 SOP 文件列表
curl http://localhost:8000/            # SPA 前端入口
```

### 方式二：本地开发（分步启动）

```bash
# 1. 启动 Elasticsearch（Docker 仅运行 ES）
docker compose up -d elasticsearch

# 2. 安装 Python 依赖并启动后端
cd backend
python -m venv venv && source venv/bin/activate   # 创建虚拟环境
pip install -r requirements.txt                    # 安装依赖

# 设置 Kimi API Key 后启动
export KIMI_API_KEY="sk-your-key"                  # Linux/macOS
# set KIMI_API_KEY=sk-your-key                     # Windows CMD
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 3. 安装前端依赖并启动开发服务器（新终端）
cd frontend
npm install
npm run dev     # → http://localhost:5173，自动代理 API 到 :8000
```

### 前端构建（生产模式）

```bash
cd frontend
npm run build     # TypeScript 编译 + Vite 打包 → dist/
```

FastAPI 会自动托管 `frontend/dist/` 作为 SPA 静态文件。Docker 部署模式下重新构建：

```bash
cd frontend && npm run build
docker compose up -d --build backend   # 重新构建并重启
```

### 访问地址

| 地址 | 说明 |
|------|------|
| `http://localhost:8000` | 应用入口（生产构建） |
| `http://localhost:5173` | 前端开发服务器（HMR 热更新） |
| `http://localhost:8000/docs` | FastAPI 自动生成的 API 文档 |
| `http://localhost:8000/v1` | Phase 1 · 关键词搜索页面 |
| `http://localhost:8000/v2` | Phase 2 · 语义搜索页面 |
| `http://localhost:8000/v3` | Phase 3 · Agent 对话页面 |

---

## API 规范

### Phase 1 · 关键词搜索

**索引文档**

```http
POST /v1/documents
Content-Type: application/json

{
  "id": "sop-001",
  "html": "<html><head><title>后端服务 On-Call SOP</title></head><body><h1>服务器 OOM 处理</h1><p>当服务器发生 OOM 时，首先使用 top/htop 确认内存占用...</p></body></html>"
}
```

```json
HTTP 201 Created
{
  "id": "sop-001",
  "title": "后端服务 On-Call SOP"
}
```

**关键词搜索**

```http
GET /v1/search?q=服务器OOM怎么办
```

```json
HTTP 200 OK
{
  "query": "服务器OOM怎么办",
  "results": [
    {
      "id": "sop-001",
      "title": "后端服务 On-Call SOP",
      "snippet": "...当服务器发生 <em>OOM</em> 时，首先使用...",
      "score": 3.456
    }
  ]
}
```

> 使用 Elasticsearch `match` 查询配合 smartcn 中文分词器，结果按 TF-IDF 相关性降序排列。`snippet` 中的匹配词以 `<em>` 标签高亮。

---

### Phase 2 · 语义搜索

```http
GET /v2/search?q=服务内存溢出怎么处理
```

```json
HTTP 200 OK
{
  "query": "服务内存溢出怎么处理",
  "results": [
    {
      "id": "sop-001",
      "title": "后端服务 On-Call SOP",
      "snippet": "# 后端服务 On-Call SOP\n\n## 1. OOM 排查\n\n1. 使用 top/htop 确认...",
      "score": 0.89
    }
  ]
}
```

> 使用 `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`（384 维）将查询和文档分别向量化，在 FAISS `IndexFlatIP` 索引上进行内积相似度搜索。相比 Phase 1 的关键词匹配，语义搜索能理解"服务器挂了"和"服务故障"之间的语义关联。

---

### Phase 3 · Agent 对话

**发送消息（SSE 流式）**

```http
POST /v3/chat
Content-Type: application/json

{
  "message": "数据库主从延迟超过 30 秒怎么处理？",
  "history": []
}
```

**SSE 事件流示例**

```
event: answer
data: {"content":"我来"}

event: answer
data: {"content":"帮您"}

event: thought
data: {"content":"正在查阅 SOP 文档...","turn":1}

event: tool_call
data: {"tool":"readFile","arguments":{"fname":"sop-002.html"}}

event: tool_result
data: {"content":"# 数据库 DBA On-Call SOP\n\n## 1. 主从延迟排查\n\n1. 检查 Slave I/O 和 SQL 线程状态\n   SHOW SLAVE STATUS\\G\n   Seconds_Behind_Master > 30s → 需要介入\n..."}

event: answer
data: {"content":"根据 SOP-002 "}

event: answer
data: {"content":"，主从延迟"}

event: answer
data: {"content":"超过 30 秒的处理步骤..."}
```

> 使用 ReAct（Reasoning + Acting）循环：模型先思考需要什么信息，调用 `readFile` 工具读取 SOP 文档（可多轮调用），观察结果后继续推理或给出最终回答。每轮对话最多调用 5 次工具。最终回答通过 SSE 流式推送，前端以打字机效果逐词展示。

**SSE 事件类型**

| 事件 | 触发时机 | data 字段 |
|------|----------|-----------|
| `thought` | 工具调用前 | `{"content": "...", "turn": 1}` |
| `tool_call` | 工具调用时 | `{"tool": "readFile", "arguments": {"fname": "..."}}` |
| `tool_result` | 工具返回后 | `{"content": "..."}` （截断至 2000 字符） |
| `answer` | 回答时（多次） | `{"content": "chunk..."}` |
| `error` | 出错时 | `{"content": "错误信息"}` |

**上传 SOP 文档**

```http
POST /v3/upload
Content-Type: multipart/form-data

file: sop-011.html
```

```json
HTTP 200 OK
{
  "success": true,
  "filename": "sop-011.html",
  "size": 12345
}
```

上传限制：
- 仅允许 `.html` 文件
- 文件名包含路径遍历字符（`..`、`/`、`\`）会被拒绝
- 最大文件大小为 `MAX_UPLOAD_SIZE_MB`（默认 10 MB）

**查看可用文件**

```http
GET /v3/files
```

```json
HTTP 200 OK
{
  "files": [
    {"name": "sop-001.html", "size": 7895, "modified": "2026-03-17T10:34:15"},
    {"name": "sop-002.html", "size": 10236, "modified": "2026-03-17T10:34:15"}
  ]
}
```

---

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `KIMI_API_KEY` | Kimi API 密钥（**必填**） | `sk-placeholder` |
| `KIMI_BASE_URL` | Kimi API 地址 | `https://api.moonshot.cn/v1` |
| `KIMI_MODEL` | 对话模型 | `kimi-k2.6` |
| `ES_HOST` | Elasticsearch 地址 | `http://localhost:9200` |
| `ES_INDEX` | ES 索引名称 | `oncall_docs` |
| `DATA_DIR` | SOP 文档目录 | `./data` |
| `EMBEDDING_MODEL` | 嵌入模型名称 | `paraphrase-multilingual-MiniLM-L12-v2` |
| `MAX_AGENT_TURNS` | Agent 最大工具调用轮数 | `5` |
| `MAX_UPLOAD_SIZE_MB` | 上传文件大小上限 | `10` |

---

## 项目特色

- **三阶段递进** — 从 TF-IDF 关键词 → 向量语义 → Agent 对话，三种检索方式各自独立，渐进增强
- **ReAct Agent** — 模型自主决策查阅哪些 SOP 文档，工具调用过程以前端时间线组件可视化
- **流式输出** — Phase 3 使用 SSE 实时推送回答，前端逐字展示，无需等待完整生成
- **对话持久化** — 基于 localStorage 的对话历史管理，支持创建/切换/删除多轮对话
- **动态 SOP 目录** — 启动时扫描 `data/` 自动生成文档目录注入 System Prompt，新增 SOP 无需改代码
- **追问引导** — 当用户问题模糊时，Agent 主动追问关键信息而非盲目查阅文档
- **文件上传** — 支持拖拽或点击上传 .html SOP 文档，含路径遍历防护、类型校验和大小限制
- **SPA 托管** — 前端构建产物由 FastAPI 直接托管，单容器即可提供完整 Web 服务
- **模型缓存** — HuggingFace 嵌入模型缓存挂载为 Docker Volume，重启无需重新下载
