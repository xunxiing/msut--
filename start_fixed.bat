@echo off
chcp 65001 >nul
echo 正在启动 MSUT 项目...
echo.

echo 激活 Python 虚拟环境...
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else (
    echo 警告: 虚拟环境未找到，使用系统Python环境
)
echo.

echo 启动后端服务（DEBUG 模式）...
set LOG_LEVEL=DEBUG
start "MSUT Server" cmd /k "set LOG_LEVEL=DEBUG && .venv\Scripts\python -m uvicorn server.app:app --reload --port 3000"
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