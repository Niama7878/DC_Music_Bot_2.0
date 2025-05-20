import asyncio
import threading
from dc_config import bot, token
import dc_command
import dc_event

async def run_bot():
    """启动 Discord Bot"""
    async with bot:
        await bot.start(token)

def start_bot():
    """线程运行 Discord Bot"""
    asyncio.run(run_bot())

threading.Thread(target=start_bot, daemon=True).start()