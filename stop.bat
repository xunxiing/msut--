@echo off
echo 正在停止MSUT项目...
echo.

echo 查找并停止Python uvicorn进程...
taskkill /f /im python.exe /fi "WINDOWTITLE eq MSUT Server*" 2>nul
echo Python uvicorn进程已停止

echo.
echo 查找并停止Node.js进程...
taskkill /f /im node.exe /fi "WINDOWTITLE eq MSUT Client*" 2>nul
echo Node.js进程已停止

echo.
echo MSUT项目已停止
pause
