# MSUT 主站 · 认证 + 资源 + 教程 RAG 系统

基于 **Python + FastAPI + Vue 3 + TypeScript** 的现代化全栈系统，用于账号认证、资源文件管理，以及教程文档的 AI 搜索与问答（RAG）。

> 后端已从 Node.js + Express 全量迁移到 **Python/FastAPI**，并保持原有 API 兼容。

---

## 🧭 架构总览

- 后端：Python 3.11+、FastAPI、Uvicorn  
  - 入口：`server/app.py`  
  - 路由：  
    - 认证与用户：`server/auth.py`  
    - 资源 / 文件上传：`server/files.py`  
    - `.melsave` 生成工具：`server/melsave.py`  
    - 教程文档 + RAG 搜索/问答：`server/tutorials.py`  
  - 数据库：SQLite（`sqlite3`），默认文件 `server/data/data.sqlite`  
  - 上传目录：`server/uploads/`（通过 `/uploads` 挂载为静态资源）  
  - 公共工具：`server/utils.py`（Cookie 选项、布尔解析、slug/nanoid 等）

- 前端：Vue 3 + TypeScript + Vite（目录：`melon-tech-web/`）  
  - 生产构建产物：`melon-tech-web/dist/`（Docker 构建阶段复制到容器 `/app/web/dist`）  
  - 开发服务器：Vite（默认端口 `5173`），代理 `/api` 到本地后端。

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

教程 RAG / LLM 相关（可选，用于“教程 + AI 搜索/问答”）：

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

### 教程 + RAG 搜索 / 问答（新增）

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

---

## 🖥 前端：文档系统 + RAG 页面

前端路由使用 Vue Router 定义，主要页面包括：

- `/`：首页  
- `/about`：关于页  
- `/resources`：资源文件列表  
- `/upload`：上传文件（需要登录）  
- `/my/resources`：作品管理中心（合并“我的存档”和“我的教程”管理，需登录）  
- `/dsl`：DSL `.melsave` 生成工具  
- `/watermark`：水印检测工具  
- `/share/:slug`：资源详情分享页  
- `/tutorials`：**教程中心 + AI 搜索/问答**
  - 统一输入框，可选择「文档搜索」「AI 问答」「搜索 + 问答」模式；  
  - 左侧展示搜索结果或教程列表，支持点击查看教程详情；  
  - 右侧展示 AI 回答（包含引用片段）与完整教程内容；  
  - 页内提供「新增教程」表单，登录后可以直接创建教程文本，自动纳入搜索 + RAG 范围。

顶部导航和侧边抽屉菜单中均提供 `/tutorials` 入口，方便用户直接进入教程 + AI 页面。

---

## 🔐 安全与运行注意事项

- 密码使用 `bcrypt` 哈希存储。  
- 身份认证基于 JWT，使用名为 `token` 的 Cookie 传递会话信息。  
- 设置 Cookie 时必须通过 `utils.cookie_kwargs()`，确保 SameSite / Secure 等选项在反向代理之后表现正确。  
- 避免在日志中打印敏感信息（如 `RAG_API_KEY` 等）。  
- SQLite 与上传目录在 Docker 中通过卷挂载持久化，避免容器销毁导致数据丢失。

---

## 🤝 参与与反馈

欢迎通过以下方式参与项目：

1. Fork 仓库  
2. 创建分支：`git checkout -b feature/my-feature`  
3. 提交改动：`git commit -m "Add my feature"`  
4. 推送分支并发起 Pull Request  

如有问题或新需求（例如扩展 RAG 能力、接入不同的 LLM 提供方），欢迎在 Issues 中提出。感谢使用 MSUT 主站。 


---

## Agent ????????
- `AGENT_API_BASE`?OpenAI ????????????? `RAG_API_BASE`?  
- `AGENT_API_KEY`?Agent ????? API Key????? `RAG_API_KEY`?  
- `AGENT_MODEL`?Agent ?????/????????? `moonshotai/Kimi-K2-Thinking`?  

## Agent ?? + ??????
- `POST /api/agent/sessions`???????????????  
- `GET /api/agent/sessions`??????????????????  
- `GET /api/agent/sessions/{id}/messages`???????????????  
- `POST /api/agent/ask`????? Agent ???body ?? `{ "message": "??", "sessionId": ?? }`??????????? `.melsave` ????????  
- `GET /api/agent/runs/{runId}`??????????????????????Agent ??? `server/agent/?????.txt` ? `server/agent/????.txt` ???????????????????????????????????  
