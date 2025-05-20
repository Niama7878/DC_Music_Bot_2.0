from typing import Optional, List, Dict, Union
from pathlib import Path
import os
import subprocess
import re
import time
from dc_config import messages, music_player
import psutil

downloaded = []
music_dir = "mp3"

def download_status(status: Optional[Dict[str, Union[str, float]]] = None, query_id: Optional[str] = None) -> Optional[Dict[str, Union[str, float]]]:
    """记录或按 ID 查询下载进度，自动清除超时项"""
    now = time.time()

    global downloaded
    downloaded = [
        item for item in downloaded
        if isinstance(item.get("timestamp"), (int, float)) and now - item["timestamp"] < 300
    ]

    if status:
        status["timestamp"] = now  
        downloaded.append(status)
    elif query_id:
        for i, item in enumerate(downloaded):
            if item.get("id") == query_id:
                return downloaded.pop(i)
    return None

def get_music(check: Optional[str] = None) -> Optional[List[Dict[str, Union[str, list]]]]:
    """返回播放列表和音乐"""
    music = []
    music_path = get_path(music_dir)

    if music_path.exists() and any(music_path.iterdir()):
        for item in music_path.iterdir():
            if item.is_dir():
                name = item.name
            elif item.is_file() and item.suffix.lower() == ".mp3":
                name = item.stem
            else:
                continue  
            
            if check and check != name:
                if not os.path.exists(get_path(music_dir, name, f"{check}.mp3")):
                    continue

            music_data = {
                "type": "playlist" if item.is_dir() else "mp3",
                "name": name if item.is_dir() else None,
                "music": (
                    [sub_item.stem for sub_item in item.iterdir() if sub_item.is_file()]
                    if item.is_dir() else
                    [item.stem]
                )
            }
            music.append(music_data)

            if check:
                break
        return music 
    return None

def get_path(folder: Optional[str] = None, subfolder: Optional[str] = None, filename: Optional[str] = None) -> Path:
    """返回合成的路径"""
    parts = [part for part in [folder, subfolder, filename] if part]
    return Path(*parts)

def verify_name(name: str) -> bool:
    """验证文件夹或文件名称"""
    invalid = re.search(r'[<>:"/\\|?*]', name)
    return bool(invalid)

def get_name(name: str) -> str:
    """获取不带扩展和路径名称"""
    itemname = os.path.basename(name)
    return os.path.splitext(itemname)[0]

def get_music_duration(filepath: str) -> tuple[float, int, int]:
    """使用 ffprobe 获取音频长度"""
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", filepath],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    total_seconds = float(result.stdout)
    minutes = int(total_seconds) // 60
    seconds = int(total_seconds) % 60
    return total_seconds, minutes, seconds

def get_player() -> dict[str, Union[str, list[str], None]]:
    """获取播放器状态"""
    first_item = music_player.play_queue[0] if music_player.play_queue else None
    from_playlist = first_item and first_item.parent != get_path(music_dir)

    player_data = {
        "play_queue": [get_name(str(path)) for path in music_player.play_queue] if from_playlist else None,
        "playlist_name": first_item.parent.name if from_playlist else None,
        "current_music": get_name(music_player.play_queue[music_player.current_track_index]) if first_item else None,
        "playback_mode": messages['playback_mode'][music_player.playback_mode],
        "current_volume": f"{int(music_player.current_volume * 100)}%"
    }
    return player_data

def check_music_open(name: str) -> bool:
    """检查音乐是否被占用"""
    player_data = get_player()
    current_music = player_data.get("current_music")

    if current_music:
        playlist_name = player_data.get("playlist_name")
        if playlist_name == name or current_music == name:
            abs_path = os.path.abspath(get_path(music_dir, playlist_name, f"{current_music}.mp3"))
            for proc in psutil.process_iter(['pid', 'open_files']):
                open_files = proc.info['open_files']
                if open_files:
                    for f in open_files:
                        if os.path.abspath(f.path) == abs_path:
                            return True
                time.sleep(0.05)
    return False

def edit_play_queue(music: Optional[Path] = None, music_name: Optional[str] = None, playlist: Optional[str] = None):
    """修改播放队列"""
    player_data = get_player()

    play_queue = player_data['play_queue']
    if not play_queue:
        return

    if music_name in play_queue:
        music_player.play_queue.remove(music)
    elif playlist == player_data['playlist_name']:
        if music_name:
            music_player.play_queue.append(music)
        else:
            music_player.play_queue = []