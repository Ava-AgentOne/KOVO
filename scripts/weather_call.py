"""Generate a weather briefing and place a real Telegram voice call."""
import asyncio
import sys
sys.path.insert(0, "/opt/kovo")

from dotenv import load_dotenv
load_dotenv("/opt/kovo/config/.env")

import edge_tts
from src.tools.telegram_call import TelegramCaller

AUDIO_PATH = "/opt/kovo/data/audio/weather_briefing.mp3"
VOICE = "en-US-GuyNeural"

BRIEFING = (
    "Good morning the owner. Here is your weather briefing for Al Ain, Tuesday March 24th. "
    "Currently: Partly cloudy, 27 degrees Celsius, humidity at 48 percent, "
    "northerly winds at 30 kilometres per hour. UV index is 6, "
    "so sunscreen is recommended if you are heading outside. "
    "For the rest of today: We will peak around 26 to 27 degrees this afternoon. "
    "Heads up — patchy light rain is expected this evening, "
    "turning to moderate rain overnight, with winds picking up to 38 kilometres per hour. "
    "Tomorrow looks similar, with rain continuing in the morning before gradually clearing. "
    "Stay dry, and have a great Tuesday!"
)

async def main():
    print("Generating TTS weather briefing...")
    c = edge_tts.Communicate(BRIEFING, VOICE)
    await c.save(AUDIO_PATH)
    print(f"Audio saved to {AUDIO_PATH}")

    caller = TelegramCaller(
        api_id=36018112,
        api_hash="b760d5b9456f0c930957e07bd7b43c41",
        call_timeout=60,
    )

    import os, httpx

    print("Placing Telegram call...")
    result = await caller.call_user(
        user_id=8339361967,
        audio_path=AUDIO_PATH,
    )
    print("Result:", result)

    # Manual fallback: send voice message via bot if call failed/unanswered
    if result.get("method") != "call":
        print("Call not answered — sending voice message fallback...")
        BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
        ESAM_ID = os.environ.get("ESAM_TELEGRAM_ID")
        async with httpx.AsyncClient() as client:
            with open(AUDIO_PATH, "rb") as f:
                resp = await client.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice",
                    data={"chat_id": ESAM_ID, "caption": "🌤 *Weather Briefing — Al Ain, Tue 24 Mar*\n_(Missed call fallback)_", "parse_mode": "Markdown"},
                    files={"voice": f},
                    timeout=60,
                )
            print("Fallback voice sent:", resp.status_code)

asyncio.run(main())
