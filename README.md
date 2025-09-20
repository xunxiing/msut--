# MSUT全栈认证系统

基于 Node.js + Express + Vue.js + TypeScript 构建的现代化全栈认证与资源管理系统！！

## 🚀 技术栈

### 后端
- **Node.js** 20.18.0 + **Express** 框架
- **TypeScript** 提供类型安全
- **SQLite** 数据库 (better-sqlite3)
- **JWT** 身份认证
- **bcryptjs** 密码加密
- **multer** 文件上传处理

### 前端
- **Vue.js** 3.5.21 + **TypeScript**
- **Vite** 构建工具
- **Element Plus** UI 组件库
- **Pinia** 状态管理
- **Vue Router** 路由管理

### 部署
- **Docker** 容器化部署
- **Nginx** 反向代理和静态文件服务
- 支持国内镜像源加速

## 📦 功能特性

- ✅ 用户注册/登录/注销
- ✅ JWT 身份认证
- ✅ 资源管理系统
- ✅ 文件上传功能
- ✅ 响应式设计
- ✅ Docker 容器化部署
- ✅ 生产环境优化

## 🛠️ 快速开始

### 环境要求
- Node.js 20.18.0+
- Docker (可选)

### 本地开发

```bash
# 安装依赖
npm install

# 启动后端开发服务器
npm run dev:server

# 启动前端开发服务器
npm run dev:client

# 同时启动前后端
npm run dev:all
```

访问地址：
- 前端: http://localhost:5173
- 后端 API: http://localhost:3000

### Docker 部署

#### 标准构建
```bash
# 构建镜像
docker build -t msut-auth-system:1.0.0 .

# 运行容器
docker run -d \
  --name msut-auth-app \
  -p 80:80 \
  -p 3000:3000 \
  -e JWT_SECRET=your-super-secret-jwt-key \
  -e NODE_ENV=production \
  -v msut-uploads:/app/server/uploads \
  --restart unless-stopped \
  msut-auth-system:1.0.0
```

#### 国内镜像源构建（推荐国内用户）
```bash
# 使用国内镜像源构建
docker build -f Dockerfile.cn -t msut-auth-system:1.0.0-cn .

# 或使用 Docker Compose
docker-compose up -d
```

#### 验证部署
```bash
# 检查容器状态
docker ps

# 测试前端访问
curl http://localhost

# 测试后端API
curl http://localhost:3000/api/auth/me

# 查看日志
docker logs msut-auth-app
```

## 📁 项目结构

```
msut主站/
├── server/                 # 后端代码
│   ├── src/
│   │   ├── auth.ts        # 认证逻辑
│   │   ├── db.ts          # 数据库连接
│   │   ├── files.ts       # 文件管理
│   │   └── index.ts       # 入口文件
│   ├── uploads/           # 上传文件目录
│   └── package.json
├── melon-tech-web/        # 前端代码
│   ├── src/
│   │   ├── api/           # API 接口
│   │   ├── components/    # 公共组件
│   │   ├── router/        # 路由配置
│   │   ├── stores/        # 状态管理
│   │   └── views/         # 页面组件
│   └── package.json
├── Dockerfile             # Docker 构建文件
├── Dockerfile.cn          # 国内镜像源版本
├── docker-compose.yml     # Docker Compose 配置
└── README.md
```

## 🔧 环境变量

### 后端环境变量
- `PORT`: 服务器端口 (默认: 3000)
- `JWT_SECRET`: JWT 密钥 (生产环境必须修改)
- `NODE_ENV`: 运行环境 (development/production)
- `PUBLIC_BASE_URL`: 公共访问地址

### 前端环境变量
- `VITE_PUBLIC_BASE_URL`: API 基础地址

## 🔐 安全特性

- ✅ 密码bcrypt加密存储
- ✅ JWT token身份验证
- ✅ Helmet安全中间件
- ✅ 非root用户运行容器
- ✅ 只读文件系统权限控制

## 🚀 生产环境部署

1. **修改JWT密钥**
   ```bash
   export JWT_SECRET=your-very-secure-random-secret-key
   ```

2. **使用Docker Compose部署**
   ```bash
   docker-compose up -d
   ```

3. **配置反向代理**（可选）
   - 使用 Nginx/Apache 作为前端代理
   - 配置 HTTPS 证书
   - 设置域名解析

## 📋 API 接口

### 认证接口
- `POST /api/auth/register` - 用户注册
- `POST /api/auth/login` - 用户登录
- `POST /api/auth/logout` - 用户注销
- `GET /api/auth/me` - 获取当前用户信息

### 资源接口
- `GET /api/resources` - 获取资源列表
- `POST /api/resources` - 创建资源（需要认证）
- `GET /api/resources/:slug` - 获取资源详情
- `POST /api/files/upload` - 上传文件（需要认证）
- `GET /api/files/:id/download` - 下载文件

## 📝 开发说明

### 数据库
项目使用 SQLite 数据库，数据文件位于 `server/data.sqlite`。首次运行会自动创建所需的表结构。

### 文件上传
上传的文件存储在 `server/uploads/` 目录，建议在生产环境中挂载外部存储卷。

### 构建优化
- 多阶段Docker构建，最小化镜像体积
- 前端资源压缩和缓存优化
- 后端依赖生产环境精简

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 🐛 常见问题

### Q: 容器启动失败怎么办？
A: 检查端口是否被占用，查看容器日志：`docker logs msut-auth-app`

### Q: 前端页面空白怎么办？
A: 确认构建是否成功，检查浏览器控制台错误信息

### Q: 文件上传失败怎么办？
A: 检查上传目录权限和磁盘空间，确认Docker卷挂载正确

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 🆘 支持

如有问题，请在 GitHub Issues 中提交问题描述。
