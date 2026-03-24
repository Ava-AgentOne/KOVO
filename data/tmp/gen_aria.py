import asyncio
import edge_tts

async def gen():
    communicate = edge_tts.Communicate(
        "Hello Esam! I'm Aria, your new voice. I'll be the one waking you up, sending you alerts, and keeping you company. Nice to meet you!",
        "en-US-AriaNeural"
    )
    await communicate.save("/opt/miniclaw/data/audio/aria_hello.mp3")

asyncio.run(gen())
print("done")
