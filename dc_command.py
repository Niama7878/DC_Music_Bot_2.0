import discord
from discord import app_commands, Interaction
import asyncio
from tools import download_status, get_music, music_dir, get_path, verify_name, get_music_duration, get_name, get_player, check_music_open, edit_play_queue
from dc_config import tree, music_choice, messages, music_player
from dc_extra import autocomplete_music_callback, ensure_voice, play_track
from downloader import download_task
from uuid import uuid4
import shutil
import os

@tree.command(name="leave", description="离开语音频道")
async def leave(interaction: Interaction):
    try:
        vc = interaction.guild.voice_client
        if vc is not None and vc.is_connected():
            await vc.disconnect()
            await interaction.response.send_message(f"已离开语音频道。", ephemeral=True)
        else:
            await interaction.response.send_message("当前没有连接到任何语音频道。", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"离开语音频道时出错: {e}", ephemeral=True)
    
@tree.command(name="download", description="下载视频为 mp3 可选播放列表")
@app_commands.describe(url="YouTube 或 Bilibili 视频链接", playlist="播放列表")
@app_commands.autocomplete(playlist=autocomplete_music_callback())
async def download(interaction: Interaction, url: str, playlist: str=None):
    try:      
        await interaction.response.defer(ephemeral=True, thinking=True)

        if playlist:
            if verify_name(playlist):
                await interaction.response.send_message('文件夹名不能包含特殊字符: `<>:"/\\|?*`')
                return
        
        id = uuid4().hex
        download_task.put({"id": id, "url": url, "folder": get_path(music_dir, filename="%(title)s.%(ext)s") if playlist is None else get_path(music_dir, playlist, "%(title)s.%(ext)s")})  
        message = await interaction.followup.send("处理中...")

        dots = ["", ".", "..", "..."]
        dot_index = 0

        while True:
            await asyncio.sleep(0.01)
            data = download_status(query_id=id)
            if data is None:
                dot_index = (dot_index + 1) % len(dots)
                await message.edit(content=f"处理中{dots[dot_index]}")
                continue

            status = data.get("status")
            extra = data.get("extra")

            if status == "error":
                await message.edit(content=f"错误: {extra}")
                return
            elif status == "downloading":
                filled = int(extra / 10)
                bar = "[" + "█" * filled + "░" * (10 - filled) + "]"
                title = data.get("title")
                await message.edit(content=(f"{playlist} / " if playlist else "") + f"{title} : {bar} {extra:.0f}%")
                if extra == 100:
                    edit_play_queue(get_path(music_dir, playlist, f"{title}.mp3"), title, playlist)
                    return
    except Exception as e:
        await interaction.followup.send(f"下载时出错: {e}", ephemeral=True)

@tree.command(name="music_view", description="查看所有音乐和播放列表中的歌曲")
async def music_view(interaction: Interaction):
    try:     
        music_data = get_music()
        if not music_data:
            await interaction.response.send_message("当前没有任何音乐或播放列表。", ephemeral=True)
            return

        msg_lines = ["**音乐列表**"]
        for music in music_data:
            type = music.get("type")
            name = music.get("music")[0] if type == "mp3" else music.get("name")
        
            if type == "playlist":
                playlist_content = "\n".join([f"- {song}" for song in music["music"]])
                msg_lines.append(f"\n**{name}**\n{playlist_content}\n")
            else:
                msg_lines.append(f"- **{name}**")

        await interaction.response.send_message("\n".join(msg_lines), ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"查看音乐和播放列表时出错: {e}", ephemeral=True)

@tree.command(name="delete_music", description="删除单曲、播放列表中的单曲或整个播放列表")
@app_commands.describe(name="要删除的音乐或播放列表")
@app_commands.autocomplete(name=autocomplete_music_callback(True, True))
async def delete_music(interaction: Interaction, name: str):
    try:
        await interaction.response.defer(ephemeral=True, thinking=True)

        music_data = get_music(name)
        if not music_data:
            await interaction.followup.send(f"未找到 `{name}`", ephemeral=True)
            return
        
        if check_music_open(name):
            await interaction.followup.send(f"`{name}` 在播放中，使用 /leave 后才可以删除", ephemeral=True)
            return

        data = music_data[0]
        type = data.get("type")
        playlist = data.get("name") 
        mp3 = f"{name}.mp3"

        if type == "mp3":
            path = get_path(music_dir, filename=mp3)
            os.remove(path)
            edit_play_queue(path, music_name=name)
        elif type == "playlist" and name == playlist:
            path = get_path(music_dir, subfolder=playlist)
            shutil.rmtree(path)
            edit_play_queue(path, playlist=playlist)
        else:
            path = get_path(music_dir, playlist, mp3)
            os.remove(path)
            edit_play_queue(path, name, playlist)
        
        await interaction.followup.send(f"已成功删除 `{name}`", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"删除音乐时出错: {e}", ephemeral=True)

@tree.command(name="player_view", description="查看当前音乐播放器状态")
async def player_view(interaction: Interaction):
    try:
        player_data = get_player()
        music = player_data.get("current_music")
        
        if not music:
            await interaction.response.send_message("当前没有正在播放的音乐。", ephemeral=True)
            return
        
        msg_lines = ["**播放器状态**"]
        msg_lines.append(f"- 当前曲目: `{music}`")
        msg_lines.append(f"- 当前音量: `{player_data['current_volume']}`")
        msg_lines.append(f"- 播放模式: `{player_data['playback_mode']}`")
        
        playlist = player_data.get("playlist_name")
        if playlist:
            msg_lines.append(f"- 当前播放列表: `{playlist}`")

        queue = player_data.get("play_queue")
        if queue:
            msg_lines.append("\n**播放队列:**")
            for i, track in enumerate(queue, start=1):
                msg_lines.append(f"{i}. `{track}`")

        await interaction.response.send_message("\n".join(msg_lines), ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"查看播放器状态时出错: {e}", ephemeral=True)
   
@tree.command(name="music", description="控制音乐播放、音量、切歌等操作")
@app_commands.choices(action=music_choice)
@app_commands.describe(action="播放控制操作", name="歌曲或播放列表名称", volume_level="音量 0~100", seek_time="跳转到指定时间，格式为秒或 mm:ss")
@app_commands.autocomplete(name=autocomplete_music_callback(include_music=True))
async def music_control(interaction: Interaction, action: app_commands.Choice[str], name: str = None, volume_level: app_commands.Range[int, 0, 100] = None, seek_time: str = None):
    try:
        value = action.value
        vc = await ensure_voice(interaction, value not in ["play", "next", "previous"])
        if vc is None:
            return
        
        if value == "play":
            if verify_name(name):
                await interaction.response.send_message('文件名不能包含特殊字符: `<>:"/\\|?*`')
                return
            
            music_data = get_music(name)
            if not music_data:
                await interaction.followup.send(f"未找到 `{name}`", ephemeral=True)
                return

            else:
                data = music_data[0]
                mp3_files = data.get("music")
                if not mp3_files:
                    await interaction.followup.send(f"播放列表 `{name}` 中没有找到任何音乐", ephemeral=True)
                    return
                
                item_dir = [get_path(music_dir, data.get("name"), f"{file}.mp3") for file in mp3_files]
                music_player.play_queue = item_dir

                _, minutes, sec = get_music_duration(music_player.play_queue[0])
                music_player.current_track_index = 0
                play_track(vc, music_player.play_queue[0])
                type = data.get("type")
                await interaction.followup.send(f"正在播放{messages['play'][type]} `{name}`"
                                                + (f"/ 歌曲 `{get_name(music_player.play_queue[0])}`" if type != "mp3" else "")
                                                + f"，{minutes} 分 {sec} 秒", ephemeral=True)

        elif value in ["pause", "resume"]:
            vc.pause() if value == "pause" else vc.resume()
            await interaction.followup.send(f"{messages['pause_resume'][value]}播放", ephemeral=True)

        elif value in ["next", "previous"]:
            if not music_player.play_queue:
                await interaction.followup.send("播放队列为空，无法切歌！", ephemeral=True)
            
            _, minutes, sec = get_music_duration(music_player.play_queue[music_player.current_track_index])

            if value == "next" and music_player.current_track_index + 1 < len(music_player.play_queue):
                music_player.current_track_index += 1
            elif value == "previous" and music_player.current_track_index > 0:
                music_player.current_track_index -= 1
            else:
                await interaction.followup.send(f"已经是{messages['next_previous'][value][0]}一首了！", ephemeral=True)
                return
            
            play_track(vc, music_player.play_queue[music_player.current_track_index])
            music_player.manual_skip = True
            await interaction.followup.send(f"{messages['next_previous'][value][1]}: `{get_name(music_player.play_queue[music_player.current_track_index])}`，{minutes} 分 {sec} 秒", ephemeral=True)

        elif value == "volume":
            if volume_level is None:
                await interaction.followup.send("请提供 0 到 100 之间的音量值！", ephemeral=True)
                return
            music_player.current_volume = volume_level / 100
            if vc.source and isinstance(vc.source, discord.PCMVolumeTransformer):
                vc.source.volume = music_player.current_volume
            await interaction.followup.send(f"音量已设置为 {volume_level}%", ephemeral=True)

        elif value in ["loop_one", "loop_all", "shuffle", "no_loop"]:
            music_player.playback_mode = value
            await interaction.followup.send(f"已设置为{messages['playback_mode'][value]}模式", ephemeral=True)

        elif value == "seek":
            if seek_time is None:
                await interaction.followup.send("请输入跳转时间，例如 90 或 1:30", ephemeral=True)
                return

            path = music_player.play_queue[music_player.current_track_index]
            duration_sec, _, _ = get_music_duration(path)

            seconds = 0
            try:
                if ":" in seek_time:
                    mins, secs = map(int, seek_time.strip().split(":"))
                    seconds = mins * 60 + secs
                else:
                    seconds = int(seek_time)
            except:
                await interaction.followup.send("无效时间格式，请输入秒数或 mm:ss 格式。", ephemeral=True)
                return

            if seconds >= duration_sec:
                seconds = int(duration_sec) - 1

            min_jump = seconds // 60
            sec_jump = seconds % 60
            await interaction.followup.send(f"跳转到 `{min_jump} 分 {sec_jump} 秒`", ephemeral=True)
            play_track(vc, path, seconds)
            music_player.manual_skip = True

    except Exception as e:
        await interaction.followup.send(f"处理音乐控制时出错: {e}", ephemeral=True)