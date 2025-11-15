# 宝塔面板Nginx代理配置指南

## 前提条件
1. 已安装宝塔面板
2. 已添加您的域名到宝塔面板
3. 已安装Docker和Docker Compose
4. 您的应用已在Docker中运行（端口：前端1122，后端3400）

## 配置步骤

### 1. 基础设置
1. 登录宝塔面板
2. 进入"网站"菜单
3. 找到您的域名，点击"设置"
4. 确保域名已解析到服务器IP

### 2. 配置反向代理（推荐方法）

#### 方法一：使用反向代理功能（简单）
1. 在域名设置页面，点击"反向代理"
2. 点击"添加反向代理"
3. 设置：
   - 代理名称：`msut-app`
   - 目标URL：`http://127.0.0.1:1122`
   - 发送域名：`$host`
4. 点击"提交"

#### 方法二：直接编辑配置文件（高级）
1. 在域名设置页面，点击"配置文件"
2. 删除默认的所有内容
3. 复制粘贴 `nginx.bt-panel.conf` 文件的内容
4. 修改以下内容：
   - `server_name your-domain.com` → 改为您的实际域名
   - SSL证书路径（如果使用HTTPS）
5. 点击"保存"

### 3. 解决冲突问题

#### 问题：不能同时设置目录代理和全局代理
**解决方案：**

**方案A：使用单一全局代理（推荐）**
- 只设置一个全局代理到 `http://127.0.0.1:1122`
- 让前端的Nginx处理路由分发
- 这是最简单的方法

**方案B：精确路径代理**
在宝塔面板的"反向代理"中添加多个规则：

1. **前端代理**：
   - 名称：`frontend`
   - 目标URL：`http://127.0.0.1:1122`
   - 路径：`/`

2. **API代理**：
   - 名称：`api`
   - 目标URL：`http://127.0.0.1:3400`
   - 路径：`/api/`

3. **文件代理**：
   - 名称：`uploads`
   - 目标URL：`http://127.0.0.1:3400`
   - 路径：`/uploads/`

### 4. 高级配置（可选）

#### 启用HTTPS
1. 在域名设置页面，点击"SSL"
2. 申请Let's Encrypt免费证书
3. 开启"强制HTTPS"

#### 缓存配置
1. 在域名设置页面，点击"缓存"
2. 根据需要开启缓存功能

#### 防火墙配置
1. 在宝塔面板主菜单，点击"防火墙"
2. 确保端口80和443是开放的

### 5. 验证配置

#### 测试命令
```bash
# 测试Nginx配置
nginx -t

# 重启Nginx服务
service nginx restart
```

#### 访问测试
- 前端：`http://your-domain.com`
- API：`http://your-domain.com/api/auth/me`
- 文件下载：`http://your-domain.com/uploads/[file-id]/download`

### 6. 常见问题解决

#### 问题1：502 Bad Gateway
**原因**：后端服务未启动或端口错误
**解决**：
```bash
# 检查Docker容器状态
docker ps

# 检查端口监听
netstat -tlnp | grep :1122
netstat -tlnp | grep :3400
```

#### 问题2：Cookie无法传递
**解决**：确保代理配置中包含：
```nginx
proxy_set_header Cookie $http_cookie;
proxy_pass_header Set-Cookie;
```

#### 问题3：文件上传失败
**解决**：调整Nginx上传大小限制：
```nginx
client_max_body_size 100M;
```

### 7. 完整配置示例

#### 简单配置（推荐新手使用）
```nginx
location / {
    proxy_pass http://127.0.0.1:1122;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

#### 完整配置（高级用户）
参考 `nginx.bt-panel.conf` 文件中的完整配置。

### 8. 注意事项

1. **端口冲突**：确保1122和3400端口没有被其他服务占用
2. **防火墙**：确保服务器防火墙允许80和443端口
3. **SELinux**：如果启用，可能需要配置SELinux规则
4. **性能**：生产环境建议开启Gzip压缩和缓存

### 9. 监控和维护

#### 日志查看
- Nginx访问日志：`/www/wwwlogs/your-domain.com.log`
- Nginx错误日志：`/www/wwwlogs/your-domain.com.error.log`

#### 性能监控
- 宝塔面板提供实时监控
- 可以安装第三方监控工具

## 技术支持
如遇到问题，可以：
1. 查看Nginx错误日志
2. 检查Docker容器状态
3. 验证网络连通性
4. 在宝塔社区寻求帮助