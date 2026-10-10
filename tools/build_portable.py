"""构建 Windows 解压即用便携包。

步骤：下载嵌入式 Python -> 安装依赖 -> 拷贝应用文件（含已构建前端）-> 写入启动脚本 -> 打包 zip。
需要：Node.js（用于构建前端，可跳过 dist 已存在时的手动构建）、网络（python.org 与 pypi 镜像）。
用法：python tools/build_portable.py [--python-version 3.12.10] [--out-version v1.0.0]
"""

import argparse
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BUILD_ROOT = REPO_ROOT / "build" / "portable"
PKG_NAME = "ebook_toolbox_portable"
CACHE_DIR = BUILD_ROOT / "cache"
DIST_DIR = REPO_ROOT / "build" / "dist"

PIP_MIRROR = "https://pypi.tuna.tsinghua.edu.cn/simple"
DEPENDENCIES = [
    "requests", "pyperclip", "selenium", "lxml", "docx2txt",
    "ebooklib", "send2trash", "pywin32", "fastapi", "uvicorn",
]

EXCLUDE_NAMES = {".git", ".env", "build", "node_modules", "__pycache__", ".venv", "venv"}
EXCLUDE_FILE_PATTERNS = ("*.pyc", "*.rar", "*.log")


def run(cmd, cwd=None):
    print(f"> {cmd if isinstance(cmd, str) else ' '.join(cmd)}")
    subprocess.run(cmd, cwd=cwd, check=True, shell=isinstance(cmd, str))


def npm_cmd(*args):
    """解析 npm 可执行文件（Windows 上是 npm.cmd）。"""
    npm = shutil.which("npm") or shutil.which("npm.cmd") or "npm"
    return [npm, *args]


def download(url: str, dest: Path):
    if dest.exists():
        print(f"缓存命中: {dest.name}")
        return
    print(f"下载 {url}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=300) as resp, dest.open("wb") as f:
        shutil.copyfileobj(resp, f)


def copy_app(pkg_app: Path):
    """拷贝应用文件，跳过排除项（.env 等敏感文件绝不进入发布包）。"""
    pkg_app.mkdir(parents=True, exist_ok=True)
    for root, dirs, files in os.walk(REPO_ROOT):
        root_path = Path(root)
        # 跳过排除目录（同时从遍历中移除）
        dirs[:] = [d for d in dirs if d not in EXCLUDE_NAMES]
        rel = root_path.relative_to(REPO_ROOT)
        # 便携包根的两个启动脚本由本脚本单独生成
        if rel == Path("."):
            files = [f for f in files if f not in ("start_web_server.bat", "download_booklist.bat")]
        for name in files:
            if name == ".env" or any(Path(name).match(pat) for pat in EXCLUDE_FILE_PATTERNS):
                continue
            src = root_path / name
            dst = pkg_app / rel / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)


def write_launchers(pkg_root: Path):
    readme = (REPO_ROOT / "使用说明.md").read_text(encoding="utf-8")
    (pkg_root / "使用说明.txt").write_text(readme, encoding="gbk", errors="replace")

    start_bat = """@echo off
title Ebook Toolbox 控制台
cd /d "%~dp0app"
echo ============================================
echo  Ebook Toolbox 电子书工具箱（便携版）
echo ============================================
echo 正在启动控制台，浏览器将自动打开 http://127.0.0.1:8000
echo 在网页中填写 Z-Library 账号、修改保存目录。
echo 停止服务：关闭本窗口即可。
echo.
"%~dp0runtime\\python\\python.exe" web_server.py
if errorlevel 1 (
  echo.
  echo 启动失败。常见原因：
  echo  - 端口 8000 已被占用（可能已有一个控制台窗口在运行）
  echo  - 解压目录路径异常，请尝试解压到较短的路径（如 D:\\ebook_toolbox）
  pause
)
"""
    dl_bat = """@echo off
title Ebook Toolbox 书单下载
cd /d "%~dp0app"
echo ============================================
echo  Ebook Toolbox 书单批量下载（便携版）
echo ============================================
echo 使用方法：先在浏览器打开 Z-Library 书单页，复制网址，再双击本文件。
echo.
echo 注意：过程中弹出的 Chrome 窗口在自动加载书单，请勿关闭它！
echo 保存位置：默认为 downloads\\booklists（可在控制台“域名与路径配置”中修改）
echo 已下载过的书自动跳过；中途失败或中断，重新双击即可续传。
echo.
"%~dp0runtime\\python\\python.exe" download_from_zlibrary_booklist.py
echo.
echo 窗口可以关闭了。
pause
"""
    (pkg_root / "启动控制台.bat").write_text(start_bat, encoding="gbk", errors="replace")
    (pkg_root / "下载书单.bat").write_text(dl_bat, encoding="gbk", errors="replace")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--python-version", default="3.12.10")
    parser.add_argument("--out-version", default="v1.0")
    args = parser.parse_args()

    py_runtime = BUILD_ROOT / PKG_NAME / "runtime" / "python"

    # 0) 前端构建（dist 缺失或强制时）
    frontend_dist = REPO_ROOT / "frontend" / "dist"
    if not (frontend_dist / "index.html").exists():
        run(npm_cmd("install"), cwd=REPO_ROOT / "frontend")
        run(npm_cmd("run", "build"), cwd=REPO_ROOT / "frontend")

    # 1) 下载并解压嵌入式 Python
    py_zip = CACHE_DIR / f"python-{args.python_version}-embed-amd64.zip"
    download(
        f"https://www.python.org/ftp/python/{args.python_version}/python-{args.python_version}-embed-amd64.zip",
        py_zip,
    )
    if py_runtime.exists():
        shutil.rmtree(py_runtime)
    py_runtime.mkdir(parents=True)
    with zipfile.ZipFile(py_zip) as zf:
        zf.extractall(py_runtime)

    # 2) 配置 _pth：加入 site-packages 与 app 目录
    ver_short = "".join(args.python_version.split(".")[:2])  # 3.12.10 -> 312
    pth = py_runtime / f"python{ver_short}._pth"
    pth.write_text(f"python{ver_short}.zip\n.\nLib/site-packages\n../../app\nimport site\n", encoding="utf-8")

    # 3) 安装依赖
    get_pip = CACHE_DIR / "get-pip.py"
    download("https://bootstrap.pypa.io/get-pip.py", get_pip)
    python_exe = str(py_runtime / "python.exe")
    run([python_exe, str(get_pip), "--no-warn-script-location", "-i", PIP_MIRROR])
    run([python_exe, "-m", "pip", "install", "--no-warn-script-location", "-i", PIP_MIRROR, *DEPENDENCIES])

    # 4) 拷贝应用文件
    pkg_root = BUILD_ROOT / PKG_NAME
    pkg_app = pkg_root / "app"
    if pkg_app.exists():
        shutil.rmtree(pkg_app)
    copy_app(pkg_app)

    # 5) 写入启动脚本
    write_launchers(pkg_root)

    # 6) 瘦身：非 Windows 组件与无用包
    site_packages = py_runtime / "Lib" / "site-packages"
    for rel in (
        "selenium/webdriver/common/macos",
        "selenium/webdriver/common/linux-x86_64",
        "selenium/webdriver/common/linux-arm64",
        "pip",
        "pythonwin",
        "PyWin32.chm",
    ):
        target = site_packages / rel
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()
    for pycache in pkg_root.rglob("__pycache__"):
        shutil.rmtree(pycache, ignore_errors=True)
    for pyc in pkg_root.rglob("*.pyc"):
        pyc.unlink(missing_ok=True)

    # 7) 打包 zip（zipfile 以 Unicode 存名，Windows 自带解压正常）
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    out_zip = DIST_DIR / f"{PKG_NAME}_win64_{args.out_version}.zip"
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as zf:
        for root, dirs, files in os.walk(pkg_root):
            dirs.sort()
            for name in sorted(files):
                full = Path(root) / name
                zf.write(full, full.relative_to(BUILD_ROOT))
    print(f"\n完成: {out_zip} ({out_zip.stat().st_size / 1024 / 1024:.1f} MB)")


if __name__ == "__main__":
    main()
