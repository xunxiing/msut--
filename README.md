# MSUT 全栈认证系统

基于 **Python + FastAPI + Vue 3 + TypeScript** 的现代化全栈认证与资源管理系统。

> 后端已从 Node.js + Express 全量迁移到 **Python/FastAPI**，并保持 API 兼容。  
> Docker 镜像同时运行 **FastAPI 后端（端口 3400）** 和一个基于 Node 的极简静态服务器 `serve`（端口 80），用于直接提供前端构建产物（容器内不集成 Nginx，推荐使用宿主机 Nginx/宝塔做反向代理与 HTTPS 终止）。

---

## 🧭 架构总览

- 后端：Python 3.11+、FastAPI、Uvicorn  
  - 入口：`server/app.py`  
  - 路由：`server/auth.py`、`server/files.py`、`server/melsave.py`  
  - 数据库：SQLite（`sqlite3`），默认文件 `server/data/data.sqlite`  
  - 上传目录：`server/uploads/`  
  - 工具：`server/utils.py`（cookie 选项、布尔解析、slug/nanoid 等）
- 前端：Vue 3 + TypeScript + Vite（目录：`melon-tech-web/`）  
  - 生产构建产物：`dist/`（Docker 构建阶段生成到容器内 `/app/web/dist`）  
  - 运行方式：容器内使用 Node `serve` 提供静态文件（监听端口 80）
- 部署建议：  
  - 使用单一 Docker 镜像，同时提供前端和后端  
  - 宿主机 Nginx 或宝塔面板负责域名、HTTPS 和反向代理：
    - `/` → `http://127.0.0.1:1122`（前端静态页面）  
    - `/api`、`/uploads` → `http://127.0.0.1:3400`（后端 API）

---

## 🧪 本地开发

### 1. 准备环境

- Python 3.11+
- Node.js 20.18.0+

### 2. 后端

```bash
python -m pip install -r server/requirements.txt

# 开发模式（自动重载）
python -m uvicorn server.app:app --reload --port 3000
```

### 3. 前端

```bash
cd melon-tech-web
npm install
npm run dev
```

默认访问：

- 前端开发：`http://localhost:5173`
- 后端 API：`http://localhost:3000`

Vite 开发服务器会将 `/api` 代理到 `http://localhost:3000`。

---

## 🐳 Docker 部署（前后端一体容器）

> Docker 镜像同时包含 **FastAPI 后端** 和一个极简静态服务器（基于 Node `serve`），用于托管前端构建产物 `/app/web/dist`。你可以只跑这一套容器，再用宿主机 Nginx/宝塔做反向代理和 HTTPS。

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

- 容器内部默认监听 `PORT=3400`（可通过环境变量覆盖），用于 FastAPI。  
- 静态前端由容器内 `serve` 提供，监听端口 80。  
- SQLite 数据库存放在容器内 `DATA_DIR/data.sqlite`（默认 `/app/server/data/data.sqlite`），建议挂载卷 `msut-data`。  
- `PUBLIC_BASE_URL` 用于生成分享链接，生产环境应配置为对外访问的真实域名（含协议）。

### 3. 使用 docker-compose

仓库中提供了 `docker-compose.yml`，会拉取或使用 ACR 中的镜像：

```bash
docker-compose up -d
```

关键点：

- 服务名：`msut-auth-app`  
- 端口映射：
  - `1122:80`（前端静态页面）  
  - `3400:3400`（后端 API）  
- 卷：
  - `./uploads:/app/server/uploads`  
  - `./data:/app/server/data`

容器内部健康检查会访问：`http://localhost:3400/api/auth/me`。

### 4. 快速验证

```bash
# 列出容器
docker ps

# 测试后端 API
curl http://localhost:3400/api/auth/me

# 查看日志
docker logs msut-auth-app
```

---

## 🌐 典型生产部署（宿主机 Nginx / 宝塔）

1. 使用 GitHub Actions / 本地构建推送镜像到 ACR：  
   - Workflow：`.github/workflows/docker-acr.yml`  
   - 默认使用 `Dockerfile` 构建并推送到：  
     `crpi-75lq6t3o28kvt0hk.cn-heyuan.personal.cr.aliyuncs.com/msut/msut-web:latest`
2. 在服务器上使用 `docker-compose up -d` 启动容器。  
3. 在宿主机 Nginx / 宝塔中配置：
   - 根路径 `/` 反向代理到 `http://127.0.0.1:1122`（前端静态站点，对应容器 80）  
   - `/api`、`/uploads` 反向代理到 `http://127.0.0.1:3400`（FastAPI 后端）  
4. 配置 HTTPS、证书与域名解析。  
5. 可参考仓库中的 `nginx.bt-panel.conf` 与 `bt-panel-setup-guide.md`。

---

## ⚙️ 环境变量

后端支持的主要环境变量：

- `PORT`  
  后端监听端口（开发默认 3000，Docker 默认 3400）。
- `JWT_SECRET`  
  JWT 密钥，生产环境必填。
- `NODE_ENV`  
  运行环境：`development` / `production`。部分安全行为（如 HSTS / Cookie secure 等）会依据此值与 `HTTPS_ENABLED`。
- `PUBLIC_BASE_URL`  
  用于生成资源分享链接，例如 `https://msut.example.com`。
- `HTTPS_ENABLED`  
  是否启用 HTTPS（影响 Cookie SameSite/secure、HSTS 等），字符串布尔值由 `utils.parse_bool` 解析。
- `COOKIE_DOMAIN`  
  Cookie 作用域域名（可选），例如 `.example.com`。
- `DATA_DIR`  
  SQLite 数据目录（默认 `server/data/`，容器中为 `/app/server/data`）。数据库文件名固定为 `data.sqlite`。

前端相关环境变量：

- `VITE_PUBLIC_BASE_URL`  
  前端调用 API 的基础地址，例如 `https://msut.example.com` 或 `http://localhost:3400`。

---

## 📋 API 一览（与原 TS 实现兼容）

### 认证接口

- `POST /api/auth/register` - 注册  
- `POST /api/auth/login` - 登录  
- `POST /api/auth/logout` - 注销  
- `GET /api/auth/me` - 获取当前用户信息

### 资源与文件

- `GET /api/resources` - 获取资源列表  
- `POST /api/resources` - 创建资源（需要登录）  
- `GET /api/resources/:slug` - 获取资源详情  
- `PATCH /api/resources/:id` - 更新资源（需要登录）  
- `DELETE /api/resources/:id` - 删除资源（需要登录）  
- `POST /api/files/upload` - 上传文件（需要登录）
  - 字段名：`files`  
  - 最多 10 个文件，单文件最大 50MB  
  - 可选表单字段 `saveWatermark`（布尔）
- `GET /api/files/:id/download` - 下载文件

### 文件点赞（新增）

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
- 实现要点：
  - 每次请求在临时目录中复制生成器代码，写入 DSL 到 `input.py`，运行流水线生成 `.melsave` 文件  
  - 响应后清理临时目录，避免并发冲突

---

## 🔐 安全与运行时注意事项

- 密码使用 `bcrypt` 哈希存储。  
- 身份认证基于 JWT，token 通过 `token` Cookie 传递。  
- 必须使用 `utils.cookie_kwargs()` 创建 Cookie，确保 SameSite / Secure 等设置在反向代理后行为正常。  
- Docker 镜像入口脚本会：
  - 初始化上传目录 `/app/server/uploads` 与数据目录 `/app/server/data`  
  - 确保 `data.sqlite` 文件存在并具备读写权限  
  - 使用 `su-exec` 以非 root 用户 `appuser` 运行 FastAPI 进程和静态服务器

---

## 🧑‍💻 贡献与支持

欢迎通过以下方式参与项目：

1. Fork 仓库  
2. 创建分支：`git checkout -b feature/my-feature`  
3. 提交改动：`git commit -m "Add my feature"`  
4. 推送分支并发起 Pull Request

如有问题或反馈，请在 GitHub Issues 中提交。感谢使用 MSUT 全栈认证系统。

