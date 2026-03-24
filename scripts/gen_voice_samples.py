"""Generate voice samples for all 4 female voices and send via Telegram."""
import asyncio
import os
import sys
sys.path.insert(0, "/opt/miniclaw")

from dotenv import load_dotenv
load_dotenv("/opt/miniclaw/config/.env")

import edge_tts
import httpx

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
ESAM_ID = os.environ.get("ESAM_TELEGRAM_ID")

TEXT = "Hi Esam! I am Ava, your personal AI assistant. How can I help you today?"

VOICES = [
    ("en-US-JennyNeural",   "1️⃣ Jenny — 🇺🇸 Friendly & warm"),
    ("en-US-AriaNeural",    "2️⃣ Aria — 🇺🇸 Natural & expressive"),
    ("en-GB-SoniaNeural",   "3️⃣ Sonia — 🇬🇧 British & professional"),
    ("en-AU-NatashaNeural", "4️⃣ Natasha — 🇦🇺 Australian & approachable"),
]

async def main():
    async with httpx.AsyncClient() as client:
        await client.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": ESAM_ID, "text": "🎙️ *Voice Samples* — reply with the number you like!\n\nSending 4 samples now...", "parse_mode": "Markdown"}
        )

        for voice, label in VOICES:
            path = f"/opt/miniclaw/data/audio/sample_{voice}.mp3"
            c = edge_tts.Communicate(TEXT, voice)
            await c.save(path)

            with open(path, "rb") as f:
                await client.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice",
                    data={"chat_id": ESAM_ID, "caption": label, "parse_mode": "Markdown"},
                    files={"voice": f},
                    timeout=30,
                )
            print(f"Sent: {label}")

        await client.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": ESAM_ID, "text": "Reply with *1, 2, 3, or 4* to set your preferred voice 👆", "parse_mode": "Markdown"}
        )

asyncio.run(main())
