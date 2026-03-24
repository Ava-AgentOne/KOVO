"""Generate a short story as a voice message and send via Telegram."""
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
VOICE = "en-US-AriaNeural"

STORY = """
Once upon a time, in the golden dunes of the Empty Quarter, a young falcon named Zayed
was afraid to leave the nest. Every morning he watched the other falcons dive and soar,
but fear held his wings still.

One evening, an old desert fox passed below and called up:
"Little falcon — the sky does not come to you. You must go to the sky."

That night, Zayed dreamed of Al Ain — its oases green, its mountains proud.
When dawn broke, he simply... stepped off the edge.

And the wind, as winds do, caught him.

He never looked down at the nest again — only forward,
toward everything that was waiting for him up there.

The end.
"""

async def main():
    path = "/opt/miniclaw/data/audio/story.mp3"
    os.makedirs(os.path.dirname(path), exist_ok=True)

    print("Generating TTS audio...")
    c = edge_tts.Communicate(STORY.strip(), VOICE)
    await c.save(path)
    print("Audio generated.")

    async with httpx.AsyncClient() as client:
        with open(path, "rb") as f:
            resp = await client.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice",
                data={"chat_id": ESAM_ID, "caption": "🦅 *A Short Story from Ava*", "parse_mode": "Markdown"},
                files={"voice": f},
                timeout=60,
            )
        print("Sent:", resp.status_code, resp.text[:200])

asyncio.run(main())
