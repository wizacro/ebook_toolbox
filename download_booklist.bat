@echo off
title Ebook Toolbox 书单下载
cd /d "%~dp0"
echo ============================================
echo  Ebook Toolbox 书单批量下载
echo ============================================
echo 使用方法：先在浏览器复制 Z-Library 书单页网址，再双击本文件。
echo.
echo 注意：过程中弹出的 Chrome 窗口在自动加载书单，请勿关闭它！
echo 保存位置：由 .env 中 BOOKLIST_SAVE_DIR 指定（可在 Web 控制台修改）
echo 已下载过的书自动跳过；中途失败或中断，重新运行即可续传。
echo.
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 download_from_zlibrary_booklist.py
) else (
  python download_from_zlibrary_booklist.py
)
echo.
echo 窗口可以关闭了。
pause
