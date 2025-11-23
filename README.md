# MSUT 主站 · 认证 + 资源 + 教程 RAG + Agent 系统

基于 **Python + FastAPI + Vue 3 + TypeScript** 的现代化全栈系统，用于账号认证、资源文件管理、教程文档的 AI 搜索与问答（RAG），以及智能 Agent 对话与代码生成。

> 后端已从 Node.js + Express 全量迁移到 **Python/FastAPI**，并保持原有 API 兼容。
> 
> 🆕 **新增 Agent 功能**：支持智能对话、代码生成、多轮会话、流式输出等特性。

---

## 🧭 架构总览

- 后端：Python 3.11+、FastAPI、Uvicorn
  - 入口：`server/app.py`
  - 路由：
    - 认证与用户：`server/auth.py`
    - 资源 / 文件上传：`server/files.py`
    - `.melsave` 生成工具：`server/melsave.py`
    - 教程文档 + RAG 搜索/问答：`server/tutorials.py`
    - **Agent 智能对话 + 代码生成：`server/agent_api.py`**
  - 数据库：SQLite（`sqlite3`），默认文件 `server/data/data.sqlite`
  - 上传目录：`server/uploads/`（通过 `/uploads` 挂载为静态资源）
  - 公共工具：`server/utils.py`（Cookie 选项、布尔解析、slug/nanoid 等）
  - **Agent 提示词文件：`server/agent/全自动生成.txt`、`server/agent/芯片教程.txt`**

- 前端：Vue 3 + TypeScript + Vite（目录：`melon-tech-web/`）
  - 生产构建产物：`melon-tech-web/dist/`（Docker 构建阶段复制到容器 `/app/web/dist`）
  - 开发服务器：Vite（默认端口 `5173`），代理 `/api` 到本地后端。
  - **Agent 界面组件：`melon-tech-web/src/components/agent/`**
    - `AgentChatWindow.vue` - 智能对话窗口
    - `AgentSidebar.vue` - 会话列表侧边栏
    - `AgentRightPanel.vue` - 任务状态面板
  - **Agent 页面：`melon-tech-web/src/views/TutorialAI.vue`** - AI 对话 + RAG 模式切换

- Docker 运行时：  
  - 容器内运行 FastAPI（端口 `3400`）+ Node `serve` 静态服务器（端口 `80`）  
  - 推荐使用宿主机 Nginx 或宝塔做反向代理、HTTPS 终止：  
    - `/` → `http://127.0.0.1:1122`（前端静态站点，对应容器 80）  
    - `/api`、`/uploads` → `http://127.0.0.1:3400`（后端 API）

---

## 🧪 本地开发

### 1. 准备环境

- Python 3.11+
- Node.js 20.18.0+

### 2. 后端启动

```bash
python -m pip install -r server/requirements.txt

# 开发模式（自动重载）
python -m uvicorn server.app:app --reload --port 3000
```

### 3. 前端启动

```bash
cd melon-tech-web
npm install
npm run dev
```

默认访问：

- 前端开发：`http://localhost:5173`
- 后端 API：`http://localhost:3000`

Vite 会将 `/api` 代理到 `http://localhost:3000`。

---

## 🐳 Docker 部署（前后端一体容器）

### 1. 本地构建镜像

```bash
# 在仓库根目录
docker build -t msut-auth-system:1.0.0 .
```

### 2. 直接运行容器

```bash
docker run -d \
  --name msut-auth-app \
  -p 1122:80 \          # 本地 1122 -> 容器 80（前端静态站点） \
  -p 3400:3400 \        # 本地 3400 -> 容器 3400（后端 API） \
  -e JWT_SECRET=your-super-secret-jwt-key \
  -e NODE_ENV=production \
  -e PUBLIC_BASE_URL=http://localhost:1122 \
  -e DATA_DIR=/app/server/data \
  -v msut-uploads:/app/server/uploads \
  -v msut-data:/app/server/data \
  --restart unless-stopped \
  msut-auth-system:1.0.0
```

说明：

- 容器内部默认监听 `PORT=3400`（可通过 `PORT` 覆盖）供 FastAPI 使用。  
- 静态前端由 `serve` 提供（监听端口 `80`）。  
- SQLite 数据库放在 `DATA_DIR/data.sqlite`（默认 `/app/server/data/data.sqlite`），建议挂载为独立卷。  
- `PUBLIC_BASE_URL` 用于生成资源分享链接，应配置为对外访问的真实域名（含协议）。

### 3. 使用 docker-compose

仓库提供了 `docker-compose.yml`，会启动一体化前后端容器并映射端口：

- `1122:80`（前端静态页面）  
- `3400:3400`（后端 API）  

数据卷：

- `./uploads:/app/server/uploads`  
- `./data:/app/server/data`  

容器内部健康检查会访问：`http://localhost:3400/api/auth/me`。

---

## ⚙️ 环境变量

后端主要环境变量：

- `PORT`  
  后端监听端口（本地开发通常为 `3000`，Docker 镜像默认 `3400`）。
- `JWT_SECRET`  
  JWT 密钥，生产环境必须配置为强随机值。
- `NODE_ENV`  
  运行环境：`development` / `production`。部分安全行为（如 HSTS / Cookie secure）取决于此值与 `HTTPS_ENABLED`。
- `PUBLIC_BASE_URL`  
  用于生成资源分享链接，例如 `https://msut.example.com`。
- `HTTPS_ENABLED`  
  是否启用 HTTPS（影响 Cookie SameSite / Secure 和 HSTS），字符串布尔通过 `utils.parse_bool` 解析。
- `COOKIE_DOMAIN`  
  Cookie 作用域域名（可选），例如 `.example.com`。
- `DATA_DIR`  
  SQLite 数据目录（默认 `server/data/`；容器内通常为 `/app/server/data`）。数据库文件名固定为 `data.sqlite`。

教程 RAG / LLM 相关（可选，用于"教程 + AI 搜索/问答"）：

- `RAG_API_BASE`
  OpenAI 兼容的 HTTP 基础地址，例如 `https://api.siliconflow.cn/v1` 或自建兼容网关地址。
- `RAG_API_KEY`
  调用 embeddings 和 chat 接口的 API Key。
- `RAG_LLM_MODEL`
  聊天模型名称，例如 `deepseek-ai/DeepSeek-V3.2-Exp`。
- `RAG_EMBED_MODEL`
  向量检索使用的 embedding 模型名称，例如 `BAAI/bge-m3`。
- `RAG_EMBED_DIM`
  向量维度（例如 `1024`），用于向量长度校验和日志记录。

Agent LLM 相关（用于智能对话 + 代码生成）：

- `AGENT_API_BASE`
  Agent 专用的 OpenAI 兼容 HTTP 基础地址，默认继承 `RAG_API_BASE`。
- `AGENT_API_KEY`
  Agent 专用的 API Key，默认继承 `RAG_API_KEY`。
- `AGENT_MODEL`
  Agent 使用的聊天模型，默认 `moonshotai/Kimi-K2-Thinking`。
  - 支持思维链模型（如 Kimi、DeepSeek V3 系列）可展示推理过程
  - DeepSeek V3.1 系列在使用工具调用时会自动关闭 thinking 模式

前端环境变量：

- `VITE_PUBLIC_BASE_URL`  
  前端调用后端 API 的基础地址，例如 `https://msut.example.com` 或 `http://localhost:3400`。

---

## 📋 API 一览

### 认证接口

- `POST /api/auth/register` - 注册
- `POST /api/auth/login` - 登录
- `POST /api/auth/logout` - 登出
- `GET /api/auth/me` - 获取当前登录用户（基于 `token` Cookie）

### 资源与文件

- `GET /api/resources` - 获取资源列表
- `POST /api/resources` - 创建资源（需要登录）
- `GET /api/resources/:slug` - 获取资源详情
- `PATCH /api/resources/:id` - 更新资源（需要登录）
- `DELETE /api/resources/:id` - 删除资源（需要登录）
- `POST /api/files/upload` - 上传文件（需要登录）
  - 字段名：`files`（最多 10 个文件，单文件最大 50MB）
  - 可选表单字段：`saveWatermark`（布尔），用于对 `.melsave` / `.zip` 进行水印提取并入库
- `GET /api/files/:id/download` - 下载文件，`Content-Disposition` 采用 UTF-8 百分号编码文件名

### 文件点赞（已实现）

- `GET /api/resources/likes?ids=1,2,3`
  返回 `{ items: [{ id, likes, liked }] }`
- `POST /api/resources/:id/like`
  点赞（幂等）返回 `{ liked: true, likes }`
- `DELETE /api/resources/:id/like`
  取消点赞返回 `{ liked: false, likes }`

### DSL 生成器（`.melsave`）

- 接口：`POST /api/melsave/generate`
  - 请求体：`{ "dsl": "..." }`
  - 响应：`.melsave` 文件字节流，`Content-Disposition` 使用 UTF-8 百分号编码文件名
- 实现要点：每次请求在临时目录中复制生成器代码，写入 DSL 到 `input.py`，运行流水线生成 `.melsave` 文件，响应后清理临时目录。

### 教程 + RAG 搜索 / 问答（已实现）

- `POST /api/tutorials` （需要登录）
  创建新的教程文档：
  ```json
  { "title": "教程标题", "description": "简介（可选）", "content": "完整正文内容" }
  ```
  保存后会自动按段落对正文进行简单分块，并调用 embedding 接口建立向量索引。

- `GET /api/tutorials`
  教程列表，可选参数：`q`（模糊搜索标题/简介/正文）、`page`、`pageSize`。
  返回：`{ items, total, page, pageSize }`。

- `GET /api/tutorials/:id`
  获取单篇教程详情及完整文本。

- `POST /api/tutorials/search-and-ask`
  统一搜索 / 问答接口：
  ```json
  {
    "query": "用户输入的问题或关键词",
    "mode": "search | qa | both",
    "limit": 6
  }
  ```
  返回示例（简化）：
  ```json
  {
    "query": "...",
    "mode": "search",
    "ragEnabled": true,
    "search": {
      "items": [
        { "tutorialId": 1, "slug": "xxx", "title": "标题", "excerpt": "片段内容", "score": 0.92 }
      ],
      "tookMs": 23
    },
    "answer": {
      "text": "AI 回答内容",
      "sources": [
        { "tutorialId": 1, "slug": "xxx", "title": "标题", "excerpt": "片段内容", "score": 0.92 }
      ]
    }
  }
  ```
  - 当未配置 `RAG_API_BASE` / `RAG_API_KEY` 等变量时，仅做基于 SQLite 的 LIKE 搜索，`ragEnabled=false`，不返回 `answer`。
  - 当配置了 RAG 时，会先对 `query` 做向量检索，选出若干教程片段作为 LLM 上下文，然后调用 `/chat/completions` 生成回答。

### Agent 智能对话 + 代码生成（新增）

- `POST /api/agent/sessions` （需要登录）
  创建新的 Agent 会话：
  ```json
  { "title": "会话标题（可选）" }
  ```
  返回：`{ "id": 会话ID, "title": "标题", "last_status": "idle" }`

- `GET /api/agent/sessions` （需要登录）
  获取当前用户的所有会话列表，返回：`{ "items": [{ id, title, last_status, last_message, created_at, updated_at }] }`

- `GET /api/agent/sessions/{session_id}/messages` （需要登录）
  获取指定会话的消息历史，支持 `limit` 参数（默认50，最大200）。

- `POST /api/agent/ask` （需要登录）
  向 Agent 发送消息：
  ```json
  {
    "message": "用户输入的问题",
    "sessionId": 123  // 可选，不提供则创建新会话
  }
  ```
  返回：`{ "sessionId": 123, "runId": 456, "created": false, "status": "pending" }`

- `GET /api/agent/runs/{run_id}` （需要登录）
  轮询任务执行状态：
  ```json
  {
    "runId": 456,
    "sessionId": 123,
    "status": "succeeded | running | failed | pending",
    "resultUrl": "/uploads/agent/xxx.melsave",  // 生成文件时的下载链接
    "resultName": "芯片文件.melsave",
    "error": "错误信息（仅失败时）"
  }
  ```

**Agent 功能特性：**
- 支持多轮对话，保持会话上下文
- 流式输出，实时显示 AI 思考过程和回答
- 智能代码生成，可调用 `generate_melsave` 工具生成 `.melsave` 文件
- 支持思维链展示，可查看 AI 的推理过程
- 自动文件下载，生成的芯片文件可直接下载
- 会话管理，支持创建、切换、查看历史会话

---

## 🖥 前端：文档系统 + RAG + Agent 页面

前端路由使用 Vue Router 定义，主要页面包括：

- `/`：首页
- `/about`：关于页
- `/resources`：资源文件列表
- `/upload`：上传文件（需要登录）
- `/my/resources`：作品管理中心（合并"我的存档"和"我的教程"管理，需登录）
- `/dsl`：DSL `.melsave` 生成工具
- `/watermark`：水印检测工具
- `/share/:slug`：资源详情分享页
- `/tutorials`：**教程中心 + AI 搜索/问答**
  - 统一输入框，可选择「文档搜索」「AI 问答」「搜索 + 问答」模式；
  - 左侧展示搜索结果或教程列表，支持点击查看教程详情；
  - 右侧展示 AI 回答（包含引用片段）与完整教程内容；
  - 页内提供「新增教程」表单，登录后可以直接创建教程文本，自动纳入搜索 + RAG 范围。
- `/tutorials/ai`：**Agent 智能对话页面**
  - **Agent 模式**：智能对话 + 代码生成，支持多轮会话、流式输出、思维链展示
  - **AI+RAG 模式**：基于教程库的智能问答，可切换模式
  - 左侧会话列表：支持创建新会话、切换历史会话、查看会话预览
  - 中央对话窗口：支持 Markdown 渲染、代码高亮、文件下载、思考过程展示
  - 右侧状态面板：实时显示任务执行状态、生成文件下载链接
  - 响应式设计：移动端自适应，支持侧边栏折叠

顶部导航和侧边抽屉菜单中均提供 `/tutorials` 和 `/tutorials/ai` 入口，方便用户直接进入教程 AI 和 Agent 页面。

---

## 🔐 安全与运行注意事项

- 密码使用 `bcrypt` 哈希存储。  
- 身份认证基于 JWT，使用名为 `token` 的 Cookie 传递会话信息。  
- 设置 Cookie 时必须通过 `utils.cookie_kwargs()`，确保 SameSite / Secure 等选项在反向代理之后表现正确。  
- 避免在日志中打印敏感信息（如 `RAG_API_KEY`、`AGENT_API_KEY` 等）。  
- SQLite 与上传目录在 Docker 中通过卷挂载持久化，避免容器销毁导致数据丢失。

---

## 🚀 Agent 功能使用指南

### 快速开始

1. **访问 Agent 页面**：导航到 `/tutorials/ai` 或点击顶部导航的 "AI 对话"
2. **选择模式**：在对话窗口底部切换 "Agent 模式" 或 "AI+RAG 模式"
3. **开始对话**：输入您的问题或需求，Agent 会智能响应

### Agent 模式特性

- **智能代码生成**：描述您的芯片需求，Agent 会生成对应的 DSL 代码并输出 `.melsave` 文件
- **多轮对话**：支持连续对话，Agent 会记住上下文信息
- **思维链展示**：可查看 AI 的推理过程，了解回答逻辑
- **实时流式输出**：回答内容实时显示，提供流畅的交互体验
- **文件自动下载**：生成的芯片文件可直接下载使用

### AI+RAG 模式特性

- **教程问答**：基于项目教程库进行智能问答
- **精准搜索**：结合向量检索和关键词搜索，快速找到相关内容
- **引用来源**：回答会显示引用的教程片段，方便查看原文

### 会话管理

- **创建新会话**：点击左侧"新建聊天"按钮
- **切换会话**：在左侧列表中选择历史会话
- **查看状态**：右侧面板实时显示任务执行状态和下载链接

### 配置要求

要使用 Agent 功能，需要配置以下环境变量：

```bash
# 基础配置（必需）
AGENT_API_BASE=https://api.siliconflow.cn/v1
AGENT_API_KEY=your-api-key
AGENT_MODEL=moonshotai/Kimi-K2-Thinking

# 或使用 RAG 配置（会自动继承）
RAG_API_BASE=https://api.siliconflow.cn/v1
RAG_API_KEY=your-api-key
```

### 支持的模型

- **推荐模型**：`moonshotai/Kimi-K2-Thinking` - 支持思维链展示
- **兼容模型**：`deepseek-ai/DeepSeek-V3.2-Exp` 等OpenAI兼容模型
- **注意事项**：DeepSeek V3.1 系列在使用工具调用时会自动关闭 thinking 模式

### 使用示例

#### 生成芯片文件
```
用户：我需要一个简单的LED闪烁芯片，频率为1Hz

Agent：我来帮您生成一个LED闪烁芯片。根据您的需求，我将创建一个频率为1Hz的LED控制电路。

[生成DSL代码并调用工具]

文件已生成：LED闪烁芯片.melsave
下载链接：[点击下载]
```

#### 教程问答
```
用户：如何使用INPUT函数？

Agent：根据教程库中的内容，INPUT函数用于...

[显示相关教程片段和详细说明]
```

---

## 🤝 参与与反馈

欢迎通过以下方式参与项目：

1. Fork 仓库  
2. 创建分支：`git checkout -b feature/my-feature`  
3. 提交改动：`git commit -m "Add my feature"`  
4. 推送分支并发起 Pull Request  

如有问题或新需求（例如扩展 RAG 能力、接入不同的 LLM 提供方、优化 Agent 功能），欢迎在 Issues 中提出。感谢使用 MSUT 主站。
