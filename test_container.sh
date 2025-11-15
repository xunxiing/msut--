#!/bin/bash

echo "=== Docker容器测试脚本 ==="
echo

# 检查容器状态
echo "1. 检查容器状态："
docker ps -a | grep msut-auth-app || echo "容器未运行"

echo
echo "2. 检查容器日志（最近50行）："
docker logs --tail 50 msut-auth-app 2>&1 | tail -20

echo
echo "3. 测试FastAPI服务："
curl -f http://localhost:3400/api/auth/me 2>/dev/null && echo "✅ FastAPI服务正常" || echo "❌ FastAPI服务无响应"

echo
echo "4. 测试Nginx代理："
curl -f http://localhost:1122/api/auth/me 2>/dev/null && echo "✅ Nginx代理正常" || echo "❌ Nginx代理失败"

echo
echo "5. 检查网络配置："
docker network inspect msut-web_msut-network 2>/dev/null | grep -A 5 -B 5 "Subnet" || echo "网络检查失败"

echo
echo "=== 测试完成 ==="