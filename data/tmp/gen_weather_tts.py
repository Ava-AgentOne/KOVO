import asyncio
import edge_tts

text = (
    "Good morning Esam. Here is your weather briefing for Al Ain, Tuesday March 24th.\n\n"
    "Currently: Partly cloudy, 27 degrees Celsius, humidity at 48 percent, "
    "northerly winds at 30 kilometres per hour. UV index is 6, so sunscreen is "
    "recommended if you are heading outside.\n\n"
    "For the rest of today: The morning started at 21 degrees and we will peak "
    "around 26 to 27 degrees this afternoon. Heads up — patchy light rain is "
    "expected this evening, turning to moderate rain overnight, with winds "
    "picking up to 38 kilometres per hour.\n\n"
    "Tomorrow looks similar, with rain continuing in the morning before gradually clearing.\n\n"
    "Stay dry, and have a great Tuesday!"
)

async def gen():
    tts = edge_tts.Communicate(text, "en-US-GuyNeural")
    await tts.save("/opt/miniclaw/data/audio/weather_briefing.mp3")
    print("TTS generated OK")

asyncio.run(gen())
