import yt_dlp
from typing import Optional
import re
from tools import download_status
import threading
import queue
import os

fragment = 6
download_task = queue.Queue()
task_id = None

def extract_url(url) -> Optional[str]:
    """提取视频网址并重构"""
    platforms = {
        "youtube_watch": {
            "head": "https://www.youtube.com/watch?",
            "patterns": {
                "v": r'[?&]v=([\w\-]+)',
            },
            "rebuild": lambda v: f"https://www.youtube.com/watch?v={v}"
        },
        "youtube_short": {
            "head": "https://youtu.be/",
            "patterns": {
                "v": r'youtu\.be/([\w\-]+)',
            },
            "rebuild": lambda v: f"https://www.youtube.com/watch?v={v}"
        },
        "bilibili": {
            "head": "https://www.bilibili.com/video/",
            "patterns": {
                "bv": r'/video/([a-zA-Z0-9]+)'
            },
            "rebuild": lambda bv: f"https://www.bilibili.com/video/{bv}"
        }
    } 

    for _, cfg in platforms.items(): 
        if url.startswith(cfg["head"]): 
            _, pattern = next(iter(cfg["patterns"].items()))
            match = re.search(pattern, url)
            if match:
                return cfg["rebuild"](match.group(1))        
    return None

def video_mp3():
    """下载视频保存为 mp3"""
    try:
        global task_id

        def hook(d: dict):
            """处理 yt_dlp 下载信息"""
            status = d.get("status", "无状态")

            if status == "downloading": 
                total = d.get("total_bytes", 0) 
                downloaded = d.get("downloaded_bytes", 0)
                extra = round(downloaded / total * 100, 2) if total else 0.0

            elif status == "error":
                extra = str(d)

            if status in ["downloading", "error"]:
                title = d.get("info_dict", {}).get("title", "无标题")
                data = {
                    "id": task_id,
                    "status": status,
                    "title": title,
                    "extra": extra,
                }
                download_status(data)

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": None,
            "postprocessors": [{   
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "320",
            }],
            "ignoreerrors": True,
            "quiet": True,
            'progress_hooks': [hook],
            "concurrent_fragment_downloads": fragment,
            #"cookiefile": "cookies.txt"
        }

        while True:
            try:
                data = download_task.get(timeout=0.01) 
                url = data.get("url")
                valid_url = extract_url(url)
                task_id = data.get("id")
                
                if valid_url:
                    folder = data.get("folder")
                    folder = str(folder).replace("\\", "/") 
                    match = re.match(r"^(.*)/\%\([^)]+\)s\.\%\([^)]+\)s$", folder)

                    os.makedirs(match.group(1), exist_ok=True) 
                    ydl_opts['outtmpl'] = folder
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([valid_url])
                else:
                    hook({"status": "error", "message": "请输入正确的 url!"})
            except queue.Empty:
                continue  
    except Exception as e:
        print(f"下载视频保存为 mp3 失败: {e}")

threading.Thread(target=video_mp3, daemon=True).start()