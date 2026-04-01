"""
Quick script: generate TTS with edge-tts and send as voice note via Telegram.
"""
import asyncio
import sys
import os

sys.path.insert(0, "/opt/kovo")

# Load env vars
from dotenv import load_dotenv
load_dotenv("/opt/kovo/config/.env")

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "***REMOVED***")
OWNER_ID  = int(os.environ.get("OWNER_TELEGRAM_ID", "123456789"))
AUDIO_OUT = "/tmp/ava_voice.mp3"

TEXT = (
    "Hi! I'm Ava, your personal AI assistant. "
    "It's wonderful to finally let you hear my voice! "
    "I'm always here whenever you need me — "
    "whether it's telecom questions, daily tasks, or just a quick chat. "
    "Talk soon! 😊"
)

VOICE = "en-US-AvaMultilingualNeural"


async def main():
    # 1. Generate TTS
    import edge_tts
    print(f"Generating TTS with voice: {VOICE}")
    communicate = edge_tts.Communicate(TEXT, VOICE)
    await communicate.save(AUDIO_OUT)
    print(f"Audio saved to {AUDIO_OUT}")

    # 2. Send via Telegram
    import telegram
    bot = telegram.Bot(token=BOT_TOKEN)
    print(f"Sending voice note to {OWNER_ID}...")
    with open(AUDIO_OUT, "rb") as f:
        await bot.send_voice(chat_id=OWNER_ID, voice=f, caption="🎙️ Hi! It's Ava — here's my voice!")
    print("Voice note sent successfully!")


if __name__ == "__main__":
    asyncio.run(main())
