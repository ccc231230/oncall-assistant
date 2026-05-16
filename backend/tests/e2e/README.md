# E2E 测试套件 (Playwright)

端到端测试覆盖 On-Call 助手的三个 Phase：关键词搜索、语义搜索、Agent 对话。

## 前置条件

### 1. 安装 Playwright

```bash
pip install pytest-playwright
playwright install chromium
```

### 2. 启动服务

**方式一：Docker Compose（推荐）**

```bash
# 在项目根目录执行
docker-compose up -d

# 等待所有服务就绪（ES healthcheck + backend startup）
docker-compose logs -f backend | grep "ready"

# 运行 E2E 测试
cd backend
pytest tests/e2e/ -v
```

**方式二：本地开发模式**

```bash
# 终端 1：启动后端（需要 ES 运行在 localhost:9200）
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 终端 2：构建前端
cd frontend
npm install && npm run build

# 终端 3：运行 E2E 测试
cd backend
pytest tests/e2e/ -v
```

## 运行测试

```bash
# 运行所有 E2E 测试
pytest tests/e2e/ -v

# 运行单个测试模块
pytest tests/e2e/test_spa_navigation.py -v
pytest tests/e2e/test_v1_search_flow.py -v

# 以 headed 模式运行（可见浏览器）
pytest tests/e2e/ -v --headed

# 降低 Playwright 日志输出
pytest tests/e2e/ -v --log-cli-level=WARNING
```

## 测试结构

```
tests/e2e/
├── conftest.py                 # Playwright 配置、健康检查、失败截图
├── test_spa_navigation.py      # SPA 路由和导航栏
├── test_v1_search_flow.py      # Phase 1 关键词搜索 (Elasticsearch)
├── test_v2_search_flow.py      # Phase 2 语义搜索 (FAISS)
├── test_v3_agent_flow.py       # Phase 3 Agent 对话 (Kimi API + SSE)
└── README.md                   # 本文件
```

## 关键 data-testid 属性

所有测试使用以下 `data-testid` 属性定位元素（禁止使用 CSS 类名）：

| 元素 | data-testid | 所属页面 |
|------|-------------|---------|
| 搜索输入框 | `search-input` | V1, V2 |
| 搜索按钮 | `search-button` | V1, V2 |
| 搜索结果容器 | `search-results` | V1, V2 |
| 结果卡片 | `result-card` | V1, V2 |
| 结果标题 | `result-title` | 组件 |
| 得分标签 | `result-score` | 组件 |
| 内容片段 | `result-snippet` | 组件 |
| 聊天输入框 | `chat-input` | V3 |
| 发送按钮 | `chat-send` | V3 |
| 聊天消息区域 | `chat-messages` | V3 |
| 用户消息 | `user-message` | V3 |
| 思考卡片 | `thought-card` | V3 |
| 工具调用卡片 | `tool-card` | V3 |
| 工具调用详情 | `toolcall-card` | 组件 |
| 回答气泡 | `answer-bubble` | V3 |
| 错误卡片 | `error-card` | V3 |
| 加载指示器 | `loading-indicator` | V3 |
| 导航 - Phase 1 | `nav-phase1` | App |
| 导航 - Phase 2 | `nav-phase2` | App |
| 导航 - Phase 3 | `nav-phase3` | App |

## 注意事项

- **Phase 3 (Agent) 测试**：需要有效的 `KIMI_API_KEY`。如果 API key 为占位符 `sk-placeholder`，测试会验证错误处理 UI 而非真实 Agent 行为。
- **失败截图**：自动保存到 `screenshot/e2e-failures/` 目录。
- **超时时间**：Agent 请求可能长达 30 秒，测试中使用了合理的等待时间。
