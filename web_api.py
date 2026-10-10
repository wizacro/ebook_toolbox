import os
import sys
import asyncio
from pathlib import Path
from textwrap import dedent
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from env_config import load_zlibrary_env, ENV_FILE

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

frontend_dist = Path(__file__).parent / "frontend" / "dist"

class EnvConfigModel(BaseModel):
    zlibrary_email: str = ""
    zlibrary_password: str = ""
    zlibrary_remix_userid: str = ""
    zlibrary_remix_userkey: str = ""
    zlibrary_domain: str = ""
    local_library_dir: str = ""
    local_output_dir: str = ""
    booklist_save_dir: str = ""
    booklist_use_local_index: str = "false"

@app.get("/api/settings")
def get_settings():
    config = load_zlibrary_env()
    return config

@app.post("/api/settings")
def save_settings(config: EnvConfigModel):
    lines = []
    if ENV_FILE.exists():
        with ENV_FILE.open("r", encoding="utf-8") as f:
            lines = f.readlines()
    
    def update_or_append(lines_arr, key, val):
        found = False
        for i, line in enumerate(lines_arr):
            if line.strip().startswith(f"{key}="):
                lines_arr[i] = f"{key}={val}\n"
                found = True
                break
        if not found:
            lines_arr.append(f"{key}={val}\n")
    
    update_or_append(lines, "ZLIBRARY_EMAIL", config.zlibrary_email)
    update_or_append(lines, "ZLIBRARY_PASSWORD", config.zlibrary_password)
    update_or_append(lines, "ZLIBRARY_REMIX_USERID", config.zlibrary_remix_userid)
    update_or_append(lines, "ZLIBRARY_REMIX_USERKEY", config.zlibrary_remix_userkey)
    update_or_append(lines, "ZLIBRARY_DOMAIN", config.zlibrary_domain)
    update_or_append(lines, "LOCAL_LIBRARY_DIR", config.local_library_dir)
    update_or_append(lines, "LOCAL_OUTPUT_DIR", config.local_output_dir)
    update_or_append(lines, "BOOKLIST_SAVE_DIR", config.booklist_save_dir)
    update_or_append(lines, "BOOKLIST_USE_LOCAL_INDEX", config.booklist_use_local_index)

    with ENV_FILE.open("w", encoding="utf-8") as f:
        f.writelines(lines)
    
    return {"status": "ok"}

@app.get("/api/scripts")
def get_scripts():
    cfg = load_zlibrary_env()
    search_default = cfg.get("local_library_dir") or "E:\\"
    output_default = cfg.get("local_output_dir") or "E:\\书单"
    return [
        {
            "id": "collect_local_ebooks",
            "name": "本地电子书搜索与整理",
            "description": "在指定硬盘中搜索书单中的电子书，并统一归档整理。",
            "params": [
                {"key": "list_dir", "label": "书单文件目录", "default": "", "tooltip": "包含书单TXT或MD的目录路径。脚本会自动读取该目录下的所有文本并提取其中带有《》的书名。必填。"},
                {"key": "clipboard_content", "label": "从剪贴板读取书单", "type": "checkbox", "default": "false", "tooltip": "勾选后从浏览器剪贴板读取书单内容（含《》标记的书名），不再需要指定书单文件目录。"},
                {"key": "search_dir", "label": "本地搜索盘符/目录", "default": search_default, "tooltip": "脚本将在此目录及其子孙目录中搜索找到的书名的电子书。耗时受目录总文件数影响。"},
                {"key": "skip_index_update", "label": "不更新索引", "type": "checkbox", "default": "false", "tooltip": "勾选后跳过文件索引的刷新检查，直接使用已有索引。适用于索引已是最新的情况，可节省等待时间。"},
                {"key": "output_dir", "label": "收集输出目录", "default": output_default, "tooltip": "找到的电子书统一存放位置，会自动为每个书单建子文件夹。"},
            ]
        },
        {
            "id": "collect_ebooks_with_booklists",
            "name": "书单批量下载 (含Z-Lib)",
            "description": "先在本地搜索匹配书单电子书，缺失的部分尝试通过Z-Library网络接口补充下载。",
            "params": [
                {"key": "list_dir", "label": "书单文件目录", "default": "", "tooltip": "包含待搜集书单文件的目录，必须确保内容已被《》包围。必填。"},
                {"key": "clipboard_content", "label": "从剪贴板读取书单", "type": "checkbox", "default": "false", "tooltip": "勾选后从浏览器剪贴板读取书单内容（含《》标记的书名），不再需要指定书单文件目录。"},
                {"key": "search_dir", "label": "本地搜索基目录", "default": search_default, "tooltip": "本地搜索的扫描起点目录。"},
                {"key": "skip_index_update", "label": "不更新索引", "type": "checkbox", "default": "false", "tooltip": "勾选后跳过文件索引的刷新检查，直接使用已有索引。适用于索引已是最新的情况，可节省等待时间。"},
                {"key": "output_dir", "label": "输出目录", "default": output_default, "tooltip": "最终电子书的保存和合并输出位置。"},
            ]
        },
        {
            "id": "zlibrary_booklist_download",
            "name": "Z-Library 书单下载（按网址）",
            "description": "解析 Z-Library 书单页网址并下载整份书单。网址留空时读取系统剪贴板；镜像域名、保存目录取上方“域名与路径配置”。",
            "params": [
                {"key": "booklist_urls", "label": "书单网址（每行一个）", "type": "textarea", "default": "", "tooltip": "在浏览器打开 Z-Library 书单页，复制地址栏网址粘贴到这里（可多行多个书单）。留空则自动读取系统剪贴板中的网址。下载过程中弹出的 Chrome 窗口请勿关闭。"},
            ]
        }
    ]

@app.websocket("/api/ws/run/{script_id}")
async def run_script_websocket(websocket: WebSocket, script_id: str):
    await websocket.accept()
    # receive params
    data = await websocket.receive_json()
    params = data.get("params", {})

    list_dir = params.get("list_dir", "").replace("\\", "\\\\")
    search_dir = params.get("search_dir", "J:\\").replace("\\", "\\\\")
    output_dir = params.get("output_dir", "J:\\书单").replace("\\", "\\\\")

    skip_index_update = params.get("skip_index_update", "false") == "true"
    use_clipboard = params.get("clipboard_content", "false") == "true"
    clipboard_text = params.get("clipboard_text", "") if use_clipboard else ""

    # 验证：仅对基于“书单文件/剪贴板文本”的脚本校验参数
    if script_id in ("collect_local_ebooks", "collect_ebooks_with_booklists"):
        if not use_clipboard and not list_dir:
            await websocket.send_text("错误：请填写书单文件目录(list_dir)或勾选'从剪贴板读取书单'！\n")
            await websocket.close()
            return

        if use_clipboard and not clipboard_text:
            await websocket.send_text("错误：已勾选'从剪贴板读取书单'，但未收到剪贴板内容！请先点击'读取剪贴板'或手动粘贴书单文本。\n")
            await websocket.close()
            return

    temp_script = Path(__file__).parent / f"temp_run_{script_id}.py"

    # 通用前导代码
    preamble = (
        "import sys\n"
        "import io\n"
        "sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')\n"
        "sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')\n"
    )

    if script_id == "collect_local_ebooks":
        if use_clipboard and clipboard_text:
            clipboard_repr = repr(clipboard_text)
            script_code = preamble + dedent(f"""\
                from pathlib import Path
                from collect_local_ebooks import (
                    check_file_list_update, generate_file_list,
                    extract_book_names, clean_dirname, process_book_list,
                )

                search_dir = r"{search_dir}"
                output_dir = Path(r"{output_dir}")

                clipboard_text = {clipboard_repr}

                print("开始执行: 本地电子书搜集（剪贴板模式）...")
                try:
                    if not {skip_index_update}:
                        if check_file_list_update(search_dir):
                            generate_file_list(search_dir)
                    else:
                        print("已跳过索引更新（使用历史索引）")

                    book_names = extract_book_names(clipboard_text)
                    if book_names:
                        lines = clipboard_text.splitlines()
                        dir_name = clean_dirname(lines[0].strip()) if lines else "新建书单"
                        print(f"从剪贴板提取到 {{len(book_names)}} 本书，目录名：{{dir_name}}")
                        output_dir.mkdir(parents=True, exist_ok=True)
                        process_book_list(
                            output_dir / "书单", search_dir,
                            from_clipboard=True, output_dir=output_dir,
                            clipboard_content=clipboard_text,
                        )
                    else:
                        print("剪贴板中未找到《》标记的书名")
                except Exception as e:
                    print(f"发生异常: {{e}}")
            """)
        else:
            script_code = preamble + dedent(f"""\
                from pathlib import Path
                from collect_local_ebooks import process_book_list_directory, check_file_list_update, generate_file_list

                list_dir = r"{list_dir}"
                search_dir = r"{search_dir}"
                output_dir = Path(r"{output_dir}")

                print("开始执行: 本地电子书搜集...")
                try:
                    if not {skip_index_update}:
                        if check_file_list_update(search_dir):
                            generate_file_list(search_dir)
                    else:
                        print("已跳过索引更新（使用历史索引）")
                    process_book_list_directory(list_dir, search_dir, output_dir=output_dir)
                except Exception as e:
                    print(f"发生异常: {{e}}")
            """)

    elif script_id == "collect_ebooks_with_booklists":
        if use_clipboard:
            clipboard_repr = repr(clipboard_text)
            script_code = preamble + dedent(f"""\
                from collect_ebooks_with_booklists import process_ebooks

                search_dir = r"{search_dir}"
                output_dir = r"{output_dir}"
                clipboard_text = {clipboard_repr}

                print("开始执行: 批量查缺补漏与下载流程（剪贴板模式）...")
                try:
                    process_ebooks("", search_dir, output_dir,
                                   skip_index_update={skip_index_update},
                                   clipboard_content=clipboard_text)
                except Exception as e:
                    print(f"发生异常: {{e}}")
            """)
        else:
            script_code = preamble + dedent(f"""\
                from collect_ebooks_with_booklists import process_ebooks

                list_dir = r"{list_dir}"
                search_dir = r"{search_dir}"
                output_dir = r"{output_dir}"

                print("开始执行: 批量查缺补漏与下载流程...")
                try:
                    process_ebooks(list_dir, search_dir, output_dir,
                                   skip_index_update={skip_index_update})
                except Exception as e:
                    print(f"发生异常: {{e}}")
            """)
    elif script_id == "zlibrary_booklist_download":
        cfg = load_zlibrary_env()
        base_url = "https://" + (cfg.get("domain") or "zh.zlib.bz").strip()
        save_dir = cfg.get("booklist_save_dir") or "E:\\zlibrary_booklists"
        local_library_dir = cfg.get("local_library_dir") or "E:\\"
        use_local_index = str(cfg.get("booklist_use_local_index", "false")).lower() == "true"
        raw_urls = [line.strip() for line in str(params.get("booklist_urls", "") or "").splitlines() if line.strip()]
        raw_urls_arg = repr(raw_urls) if raw_urls else "None"
        script_code = preamble + dedent(f"""\
            from pathlib import Path
            from download_from_zlibrary_booklist import process_booklists_from_clipboard

            print("开始执行: Z-Library 书单下载...")
            print("镜像域名: " + {base_url!r})
            print("保存目录: " + {save_dir!r})

            try:
                process_booklists_from_clipboard(
                    Path({save_dir!r}),
                    base_url={base_url!r},
                    local_library_path=Path({local_library_dir!r}),
                    use_local_index={use_local_index},
                    raw_urls={raw_urls_arg},
                )
            except Exception as e:
                print(f"发生异常: {{e}}")
        """)
    else:
        await websocket.send_text("未知的脚本运行请求")
        await websocket.close()
        return

    with temp_script.open("w", encoding="utf-8") as f:
        f.write(script_code)

    process = await asyncio.create_subprocess_exec(
        sys.executable, str(temp_script),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=str(Path(__file__).parent)
    )

    try:
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            await websocket.send_text(line.decode("utf-8", errors="replace"))

        await process.wait()
        await websocket.send_text(f"\n[进程结束，退出码：{process.returncode}]")
    except Exception as e:
        await websocket.send_text(f"错误: {str(e)}")
    finally:
        if temp_script.exists():
            try:
                temp_script.unlink()
            except:
                pass
        await websocket.close()

if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
