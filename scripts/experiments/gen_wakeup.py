import asyncio
import edge_tts

async def gen():
    text = "Good morning Esam! Rise and shine, it's time to start your day. This is Ava, ready whenever you are!"
    communicate = edge_tts.Communicate(text, "en-US-AvaMultilingualNeural")
    await communicate.save("/opt/miniclaw/data/wakeup_call.mp3")
    print("done")

asyncio.run(gen())
