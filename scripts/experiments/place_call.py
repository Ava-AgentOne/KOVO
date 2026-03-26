import asyncio
import sys
sys.path.insert(0, '/opt/kovo')
from src.tools.telegram_call import TelegramCaller

caller = TelegramCaller(
    api_id=36018112,
    api_hash='b760d5b9456f0c930957e07bd7b43c41',
    call_timeout=60
)

result = asyncio.run(caller.call_user(
    user_id=8339361967,
    audio_path='/opt/kovo/data/wakeup_call.mp3'
))
print('Result:', result)
