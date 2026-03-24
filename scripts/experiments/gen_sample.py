import asyncio
import edge_tts

async def gen():
    text = "Hey Esam! This is Ava — the Multilingual Neural voice. How does this sound for your wake up calls?"
    communicate = edge_tts.Communicate(text, "en-US-AvaMultilingualNeural")
    await communicate.save("/opt/miniclaw/data/sample_miniclaw.mp3")
    print("done")

asyncio.run(gen())
