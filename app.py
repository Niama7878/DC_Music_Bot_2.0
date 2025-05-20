from flask import Flask, render_template, request, Response
from flask_socketio import SocketIO
import os
from uuid import uuid4
from tools import get_player, get_music, music_dir, get_path, verify_name, download_status, get_name, check_music_open, edit_play_queue
from downloader import download_task, extract_url
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from typing import Dict, Union
from dotenv import load_dotenv
import shutil
import re
import dc

load_dotenv() 

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")  
socketio = SocketIO(app, async_mode="threading", cors_allowed_origins="*")

connected_sids = set()

def get_player_data() -> Dict[str, str]:
    """获取播放器状态"""
    try:
        player_data = get_player()
        music = player_data.get("current_music")
        if not music:
            return {"updated_type": "player_status_updated", "message": "当前没有正在播放的音乐。"}

        msg_lines = ["<strong><i class='fas fa-compact-disc'></i> 播放器状态</strong>"]
        msg_lines.append(f"- 当前曲目: <code class='player-info-value'>{music}</code>")
        msg_lines.append(f"- 当前音量: <code class='player-info-value'>{player_data.get('current_volume', 'N/A')}</code>")
        msg_lines.append(f"- 播放模式: <code class='player-info-value'>{player_data.get('playback_mode', 'N/A')}</code>")
        
        playlist = player_data.get("playlist_name")
        if playlist:
            msg_lines.append(f"- 当前播放列表: <code class='player-info-value'>{playlist}</code>")
        queue = player_data.get("play_queue")

        if queue:
            msg_lines.append("<br><strong><i class='fas fa-list-ol'></i> 播放队列:</strong>")
            for i, track in enumerate(queue, start=1):
                msg_lines.append(f"{i}. <code class='player-info-value'>{track}</code>")

        return {"updated_type": "player_status_updated", "message": "<br>".join(msg_lines)}
    except Exception as e:
        return {"updated_type": "player_status_updated", "error": f"查看播放器状态时出错: {str(e)}"}

def get_music_data() -> Dict[str, Union[str, list]]:
    """获取音乐数据"""
    try:
        music_data = get_music()
        if not music_data:
            return {"updated_type": "music_library_updated", "message": "当前没有任何音乐或播放列表。"}

        music_list = []
        for music in music_data:
            type = music.get("type")
            name = music.get("music")[0] if type == "mp3" else music.get("name")
            path = [{"name": song, "path": f"/mp3/{name}/{song}.mp3"} for song in music['music']] if type == "playlist" else f"/mp3/{name}.mp3"
                
            music_list.append({
                "type": type,
                "name": name,
                "path": path
            })
        return {"updated_type": "music_library_updated", "music_list": music_list}
    except Exception as e:
        return {"updated_type": "music_library_updated", "error": f"查看音乐和播放列表时出错: {str(e)}"}
    
@app.route("/")
def index() -> Response:
    """返回网站主页面"""
    return render_template("index.html")

@app.route("/mp3/download", methods=['POST'])
def download_event() -> Response:
    """处理提交的下载请求"""
    try:
        data = request.json
        url = data.get("url")
        playlist = data.get("playlist")

        if not url:
            return {"status": "error", "message": "URL 不能为空"}, 400
        if not extract_url(url):
            return {"status": "error", "message": "无效的视频链接格式"}, 400
        if playlist and verify_name(playlist):
            return {"status": "error", "message": f'播放列表文件夹名 "{playlist}" 包含无效字符'}, 400

        download_id = uuid4().hex
        for connected in list(connected_sids):
            sid = dict(connected)['sid']
            if data['sid'] == sid:
                connected_sids.remove(connected)
                connected_sids.add(frozenset({"sid": sid, "id": download_id, "playlist": playlist}.items()))
                download_task.put({
                    "id": download_id,
                    "url": url,
                    "folder": get_path(music_dir, playlist, "%(title)s.%(ext)s") if playlist else get_path(music_dir, filename="%(title)s.%(ext)s")
                })
                return {"status": "pending", "message": "下载任务已提交"}
        
        return {"status": "error", "message": "请确保以连接服务器"}
    except Exception as e:
        return {"status": "error", "message": f"下载请求处理失败: {str(e)}"}, 500
    
@app.route("/mp3/delete", methods=['POST'])
def delete_event() -> Response:
    """处理提交的删除请求"""
    try:
        data = request.json
        item_path = data.get("item_path")

        if not item_path:
            return {"status": "error", "message": "删除对象不能为空"}, 
        
        name = get_name(item_path)
        music_data = get_music(name)
        if not music_data:
            return {"status": "error", "message": f"未找到 {name}"}, 400
        
        if check_music_open(name):
            return {"status": "error", "message": f"{name} 在播放中，前往 Discord 机器人所在公会使用 /leave 后才可以删除"}, 400
        
        path = get_path(music_dir, filename=re.sub(r'^/mp3/', '', item_path))
        if os.path.isfile(path):
            playlist = False
            if path.parent.name != "mp3":
                playlist = True
            os.remove(path)
            edit_play_queue(path, get_name(path), path.parts[1] if playlist else None)
        else:
            shutil.rmtree(path)
            edit_play_queue(path, playlist=get_name(path))

        return {"status": "success", "message": f"已成功删除 {name}"}
    except Exception as e:
        return {"status": "error", "message": f"删除请求处理失败: {str(e)}"}, 500
    
@socketio.on("disconnect")
def disconnect_handler():
    """客户端断开连接"""
    sid = request.sid
    for connected in list(connected_sids):
        if sid == dict(connected)['sid']:
            connected_sids.discard(connected)
            break

def download_status_update():
    """根据 ID 获取下载进度，推送给对应的客户端"""
    while True:
        for connected in list(connected_sids):
            connected_data = dict(connected)
            id = connected_data.get("id")
            if id:
                status_data = download_status(query_id=id)
                if status_data:
                    status_data['updated_type'] = "download_status_updated"
                    sid = connected_data.get("sid")
                    socketio.emit("update_status", status_data, to=sid)
                    if status_data.get("extra") == 100:
                        title = status_data.get("title")
                        playlist = connected_data.get("playlist")
                        edit_play_queue(get_path(music_dir, playlist, f"{title}.mp3"), title, playlist)
                        connected_sids.discard(connected)
                        connected_sids.add(frozenset({"sid": sid}.items()))

        socketio.sleep(0.5)

@socketio.on("update_status")
def update_status_handler():
    """客户端请求监听状态"""
    sid = request.sid
    socketio.emit("update_status", get_player_data(), to=sid)
    socketio.emit("update_status", get_music_data(), to=sid)
    connected_sids.add(frozenset({"sid": sid}.items()))

def player_status_update():
    """播放器状态变化，推送给所有监听中的客户端"""
    last_data = None

    while True:
        try:
            player_data = get_player_data()
            data = player_data
        except Exception as e:
            data = {"error": str(e)}

        if player_data != last_data:
            for sid in list(connected_sids):
                socketio.emit("update_status", data, to=dict(sid)['sid'])
            last_data = player_data

        socketio.sleep(0.5)

class MusicDirEventHandler(FileSystemEventHandler):
    """音乐目录监听器"""
    def on_any_event(self, event: FileSystemEvent):
        """音乐目录数据变化，推送给所有监听中的客户端"""
        if event.event_type in ["created", "deleted", "moved"]:
            data = get_music_data()
            for sid in list(connected_sids):
                socketio.emit("update_status", data, to=dict(sid)['sid'])

def start_music_observer():
    """启动音乐目录监听"""
    try:
        os.makedirs(music_dir, exist_ok=True)
        event_handler = MusicDirEventHandler()

        observer = Observer()
        observer.schedule(event_handler, music_dir, recursive=True)
        observer.start()
    except Exception as e:
        print(f"音乐目录监听启动失败: {e}")

start_music_observer()
socketio.start_background_task(target=player_status_update)
socketio.start_background_task(target=download_status_update)
socketio.run(app, host="0.0.0.0", port=5000, debug=False, use_reloader=False, allow_unsafe_werkzeug=True)