@echo off
echo 正在启动MSUT项目...
echo.

echo 激活Python虚拟环境...
call .venv\Scripts\activate
echo.

echo 启动后端服务器...
start "MSUT Server" cmd /k "uvicorn server.app:app --reload --port 3000"

echo.
echo 等待后端服务器启动...
timeout /t 5 /nobreak >nul

echo.
echo 启动前端开发服务器...
start "MSUT Client" cmd /k "npm run dev:client"

echo.
echo 项目启动完成！
echo 后端服务器地址: http://localhost:3000
echo 前端开发服务器地址: http://localhost:5173 (通常)
echo.
echo 按任意键关闭此窗口...
pause >nul
