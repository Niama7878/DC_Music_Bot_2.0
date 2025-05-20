import discord
from discord import app_commands, Interaction, FFmpegPCMAudio, VoiceClient
import asyncio
from typing import Optional, List, Callable, Awaitable
import random
from dc_config import bot, music_player
from tools import get_music

async def ensure_voice(interaction: Interaction, check_voice: bool=False) -> Optional[VoiceClient]:
    """确保 bot 加入语音频道"""
    try:
        await interaction.response.defer(ephemeral=True, thinking=True)
        voice_state = interaction.user.voice

        if voice_state is None or voice_state.channel is None:
            await interaction.followup.send("你需要先加入一个语音频道！")
            return None

        channel = voice_state.channel
        vc = interaction.guild.voice_client

        if vc is None or not vc.is_connected():
            vc = await channel.connect()
            await interaction.followup.send(f"已加入频道: {channel.name}")
        elif vc.channel != channel:
            await vc.move_to(channel)
            await interaction.followup.send(f"已移动到频道: {channel.name}")

        if check_voice and (not vc.is_playing() and not vc.is_paused()):
            await interaction.followup.send("当前没有正在播放的音频。", ephemeral=True)
            return 

        return vc
    except Exception as e:
        await interaction.followup.send(f"连接语音频道失败: {e}")
        return None

def play_track(voice_client: VoiceClient, path: str, seek_sec: int = 0):
    """播放音乐"""
    before_opts = f"-ss {seek_sec}" if seek_sec > 0 else None
    source = FFmpegPCMAudio(path, before_options=before_opts)
    source = discord.PCMVolumeTransformer(source, volume=music_player.current_volume)
    
    if voice_client.is_playing():
        voice_client.stop()

    voice_client.play(source, after=lambda error: after_playing_callback(error, voice_client))

def after_playing_callback(error: Optional[Exception], voice_client):
    """after_playing 回调函数"""
    async def after_playing():
        """音乐播放结束触发"""
        if music_player.manual_skip:
            music_player.manual_skip = False
            return

        if music_player.playback_mode == "shuffle":
            music_player.current_track_index = random.randint(0, len(music_player.play_queue) - 1)

        elif music_player.playback_mode == "loop_all":
            music_player.current_track_index = (music_player.current_track_index + 1) % len(music_player.play_queue)

        elif music_player.playback_mode == "no_loop":
            if music_player.current_track_index + 1 < len(music_player.play_queue):
                music_player.current_track_index += 1

        play_track(voice_client, music_player.play_queue[music_player.current_track_index])
    
    if error:
        raise error
    asyncio.run_coroutine_threadsafe(after_playing(), bot.loop)

def autocomplete_music_callback(include_music: bool = False, include_playlist_music: bool = False) -> Callable[[Interaction, str], Awaitable[List[app_commands.Choice[str]]]]:
    """autocomplete_music 回调函数"""
    async def autocomplete_music(interaction: Interaction, current: str) -> List[app_commands.Choice[str]]:
        """补全播放列表和音乐选项 """
        music_data = get_music()
        choices = []

        if music_data:
            for music in music_data:
                type = music.get("type")
                name = music["music"][0] if type == "mp3" else music["name"]

                if type == "mp3" and not include_music:
                    continue

                choices.append(app_commands.Choice(name=f"{name} (播放列表)" if type == "playlist" else name , value=name))
                if type == "playlist" and include_playlist_music:
                    for song in music["music"]:
                        choices.append(app_commands.Choice(name=f"- {song}" , value=song))
        return choices
    
    return autocomplete_music