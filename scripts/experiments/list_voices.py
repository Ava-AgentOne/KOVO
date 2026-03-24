import asyncio
import edge_tts

async def list_voices():
    voices = await edge_tts.list_voices()
    en = [v for v in voices if v['Locale'].startswith('en')]
    for v in en:
        print(v['ShortName'], '|', v['Gender'], '|', v['Locale'])

asyncio.run(list_voices())
