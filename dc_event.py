from dc_config import tree, bot, voice_timeout_tasks, music_player
from discord import Message, Member, VoiceState
import asyncio

@bot.event
async def on_voice_state_update(member: Member, before: VoiceState, after: VoiceState):
    """bot 所在语音频道无用户时，倒计时自动断开，断开连接时重置播放器"""
    if member.bot and before.channel is not None and after.channel is None:
        music_player.play_queue = []
        music_player.current_track_index = 0
        music_player.current_volume = 0.60
        music_player.playback_mode = "no_loop"

    vc = member.guild.voice_client
    if not vc or not vc.channel:
        return
   
    bot_channel = vc.channel
    bot_channel_id = bot_channel.id

    affected_channel_ids = set()
    if before.channel:
        affected_channel_ids.add(before.channel.id)
    if after.channel:
        affected_channel_ids.add(after.channel.id)
    if bot_channel_id not in affected_channel_ids:
        return

    if all(user.bot for user in bot_channel.members):
        if bot_channel_id in voice_timeout_tasks:
            return  

        async def disconnect_after_timeout():
            try:
                await asyncio.sleep(300)  
                if all(user.bot for user in bot_channel.members):
                    await vc.disconnect()
            except asyncio.CancelledError:
                pass
            finally:
                voice_timeout_tasks.pop(bot_channel_id, None)

        task = asyncio.create_task(disconnect_after_timeout())
        voice_timeout_tasks[bot_channel_id] = task
    else:
        task = voice_timeout_tasks.pop(bot_channel_id, None)
        if task:
            task.cancel()

@bot.event
async def on_message(message: Message):
    """处理收到的信息"""
    if message.author == bot.user:
        return  

@bot.event
async def on_ready():
    """bot 启动后触发"""
    await tree.sync()  
    print(f"{bot.user} 成功启动！") 