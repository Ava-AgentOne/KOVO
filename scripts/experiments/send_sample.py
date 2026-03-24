import asyncio
import os
from telegram import Bot

async def send():
    bot = Bot(token=os.environ["TELEGRAM_BOT_TOKEN"])
    with open("/opt/miniclaw/data/sample_miniclaw.mp3", "rb") as f:
        await bot.send_voice(
            chat_id=REDACTED_USER_ID,
            voice=f,
            caption="🎙️ *en-US-AvaMultilingualNeural*",
            parse_mode="Markdown"
        )
    print("sent")

asyncio.run(send())
