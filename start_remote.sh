#!/bin/bash

echo "=== MSUT远程镜像启动脚本 ==="
echo

# 创建必要的目录
echo "1. 创建数据目录..."
mkdir -p uploads data

# 停止旧容器
echo "2. 停止旧容器..."
docker stop msut-backend 2>/dev/null || true
docker rm msut-backend 2>/dev/null || true

# 启动后端服务（使用远程镜像）
echo "3. 启动后端服务（使用远程镜像）..."
docker-compose -f docker-compose.remote.yml up -d

# 等待服务启动
echo "4. 等待服务启动..."
sleep 15

# 健康检查
echo "5. 健康检查..."
if curl -f http://localhost:3400/api/auth/me >/dev/null 2>&1; then
    echo "✅ 后端服务启动成功！"
    echo "API地址：http://localhost:3400"
    echo
    echo "📋 下一步："
    echo "1. 配置你的外部nginx，参考 nginx.external.conf"
    echo "2. 构建前端：cd melon-tech-web && npm run build"
    echo "3. 将前端文件放到你的nginx静态文件目录"
    echo "4. 重启你的外部nginx服务"
    echo
    echo "🔗 外部nginx应该代理到：http://localhost:3400"
else
    echo "❌ 服务启动失败，检查日志："
    docker logs msut-backend --tail 50
    echo
    echo "🔍 调试信息："
    echo "容器状态：$(docker ps -a | grep msut-backend)"
    echo "端口监听：$(netstat -tlnp 2>/dev/null | grep 3400 || ss -tlnp 2>/dev/null | grep 3400 || echo '无法检测端口')"
    exit 1
fi

echo
echo "=== 启动完成 ==="