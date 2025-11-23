@echo off
chcp 65001 >nul
echo 正在启动 MSUT 项目...
echo.

REM 检查虚拟环境
if exist ".venv\Scripts\activate.bat" (
    echo 激活 Python 虚拟环境...
    call .venv\Scripts\activate.bat
) else (
    echo 警告: 虚拟环境未找到，使用系统Python环境
)
echo.

echo 启动后端服务...
set LOG_LEVEL=DEBUG
python -m uvicorn server.app:app --reload --port 3000