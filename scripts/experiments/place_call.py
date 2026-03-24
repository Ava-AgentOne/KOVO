import asyncio
import sys
sys.path.insert(0, '/opt/miniclaw')
from src.tools.telegram_call import TelegramCaller

caller = TelegramCaller(
    api_id=REDACTED_API_ID,
    api_hash='REDACTED_API_HASH',
    call_timeout=60
)

result = asyncio.run(caller.call_user(
    user_id=REDACTED_USER_ID,
    audio_path='/opt/miniclaw/data/wakeup_call.mp3'
))
print('Result:', result)
