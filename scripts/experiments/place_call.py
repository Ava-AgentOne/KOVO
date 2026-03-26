import asyncio
import sys
sys.path.insert(0, '/opt/kovo')
from src.tools.telegram_call import TelegramCaller

caller = TelegramCaller(
    api_id=***REMOVED***,
    api_hash='***REMOVED***',
    call_timeout=60
)

result = asyncio.run(caller.call_user(
    user_id=123456789,
    audio_path='/opt/kovo/data/wakeup_call.mp3'
))
print('Result:', result)
