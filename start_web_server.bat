@echo off
title Ebook Toolbox Server
cd /d "%~dp0"
echo 正在启动 Ebook Toolbox，浏览器将自动打开 http://127.0.0.1:8000
echo 停止服务：关闭本窗口即可。
echo.
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 web_server.py
) else (
  python web_server.py
)
if errorlevel 1 (
  echo.
  echo 服务异常退出。可能原因：
  echo  - 未安装 Python 3.10 及以上版本（安装时请勾选 Add Python to PATH）
  echo  - 端口 8000 已被占用，可能已有一个 Ebook Toolbox 正在运行
  pause
)
