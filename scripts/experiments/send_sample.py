import asyncio
import os
from telegram import Bot

async def send():
    bot = Bot(token=os.environ["TELEGRAM_BOT_TOKEN"])
    with open("/opt/kovo/data/sample_kovo.mp3", "rb") as f:
        await bot.send_voice(
            chat_id=8339361967,
            voice=f,
            caption="🎙️ *en-US-AvaMultilingualNeural*",
            parse_mode="Markdown"
        )
    print("sent")

asyncio.run(send())
