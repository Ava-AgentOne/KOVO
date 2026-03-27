import asyncio
import edge_tts

async def gen():
    text = "Hey the owner! This is Ava — the Multilingual Neural voice. How does this sound for your wake up calls?"
    communicate = edge_tts.Communicate(text, "en-US-AvaMultilingualNeural")
    await communicate.save("/opt/kovo/data/sample_kovo.mp3")
    print("done")

asyncio.run(gen())
