import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import os

load_dotenv() 
token = os.getenv("DISCORD_BOT_TOKEN")  

intents = discord.Intents.all() 
bot = commands.Bot(command_prefix="/", intents=intents)  
tree = bot.tree  

class MusicPlayer:
    def __init__(self):
        """音乐播放器"""
        self.play_queue = []
        self.current_track_index = 0
        self.current_volume = 0.60
        self.playback_mode = "no_loop"
        self.manual_skip = False
    
music_player = MusicPlayer()

messages = {
    "play": {
        "mp3": "",
        "playlist": "播放列表"
    },
    "pause_resume": {
        "pause": "已暂停",
        "resume": "继续"
    },
    "next_previous": {
        "next": ["最后", "下一首"],
        "previous": ["第", "上一首"]
    },
    "playback_mode": {
        "loop_one": "单曲循环",
        "loop_all": "播放列表循环",
        "shuffle": "随机播放",
        "no_loop": "播放完停止",
    }
}

music_choice = [
    app_commands.Choice(name="播放", value="play"),
    app_commands.Choice(name="暂停", value="pause"),
    app_commands.Choice(name="恢复", value="resume"),
    app_commands.Choice(name="下一首", value="next"),
    app_commands.Choice(name="上一首", value="previous"),
    app_commands.Choice(name="音量", value="volume"),
    app_commands.Choice(name="单曲循环", value="loop_one"),
    app_commands.Choice(name="播放列表循环", value="loop_all"),
    app_commands.Choice(name="随机播放", value="shuffle"),
    app_commands.Choice(name="播放完停止", value="no_loop"),
    app_commands.Choice(name="跳转", value="seek"),
]

voice_timeout_tasks = {} 