"""
Telegram voice caller using Pyrogram userbot + py-tgcalls.

Architecture:
- A Pyrogram userbot (second account) places the actual call
- py-tgcalls handles WebRTC audio streaming
- Falls back to a voice message via the main bot if call unanswered
- Session health checked every 6 hours via heartbeat
"""
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

log = logging.getLogger(__name__)

_SESSION_DIR = Path("/opt/miniclaw/data")
_SESSION_DIR.mkdir(parents=True, exist_ok=True)


class CallerSessionError(Exception):
    """Raised when the userbot session is invalid or expired."""
    pass


class TelegramCaller:
    def __init__(
        self,
        api_id: int,
        api_hash: str,
        session_name: str = "miniclaw_caller",
        call_timeout: int = 30,
    ):
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_name = session_name
        self.call_timeout = call_timeout
        self._app = None
        self._calls = None

    def _get_pyrogram_app(self):
        """Create or return the Pyrogram client."""
        from pyrogram import Client
        return Client(
            self.session_name,
            api_id=self.api_id,
            api_hash=self.api_hash,
            workdir=str(_SESSION_DIR),
        )

    async def check_session_health(self) -> bool:
        """
        Verify the userbot session is alive.
        Returns True if healthy, False if expired/invalid.
        """
        try:
            app = self._get_pyrogram_app()
            async with app:
                me = await app.get_me()
                log.info("Caller session healthy: %s", me.phone_number)
                return True
        except Exception as e:
            err_name = type(e).__name__
            if any(x in err_name for x in ("AuthKey", "Session", "Deactivated", "Flood")):
                log.error("Caller session expired: %s", e)
                return False
            log.warning("Caller session check error (may be transient): %s", e)
            return None  # Unknown — don't panic

    async def call_user(
        self,
        user_id: int,
        audio_path: str,
        tg_bot=None,
        bot_chat_id: int | None = None,
    ) -> dict:
        """
        Place a Telegram voice call to user_id, playing audio_path once.
        Falls back to a voice message via tg_bot if the call fails.

        Returns: {method: "call"|"voice_message"|"failed", status: str}
        """
        try:
            await self._do_call(user_id, audio_path)
            return {"method": "call", "status": "delivered"}
        except Exception as e:
            log.warning("Call failed (%s), falling back to voice message", e)

        # Fallback: send voice message using the same audio file
        if tg_bot and bot_chat_id:
            try:
                if Path(audio_path).exists():
                    await tg_bot.send_voice(
                        chat_id=bot_chat_id,
                        voice=open(audio_path, "rb"),
                    )
                    return {"method": "voice_message", "status": "delivered"}
            except Exception as e:
                log.error("Voice message fallback failed: %s", e)

        return {"method": "failed", "status": "error"}

    async def _do_call(self, user_id: int, audio_path: str) -> bool:
        """
        Internal: place the call using py-tgcalls.
        audio_path should be an MP3 — MediaStream decodes encoded audio natively.

        Flow:
          1. play() rings the recipient and starts streaming once they answer.
          2. Wait for StreamEnded(MICROPHONE) — audio finished playing.
          3. Hang up.

        Raises on failure or if the call is not answered within call_timeout.
        """
        try:
            from pytgcalls import PyTgCalls
            from pytgcalls.types import MediaStream, ChatUpdate, StreamEnded, Device
            from pytgcalls.types.calls import CallConfig
        except ImportError as e:
            raise RuntimeError(f"py-tgcalls not available: {e}")

        if not Path(audio_path).exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        app = self._get_pyrogram_app()
        pytgcalls = PyTgCalls(app)

        audio_done = asyncio.Event()
        call_ended = asyncio.Event()

        async def _on_update(client, update):
            if isinstance(update, ChatUpdate) and update.chat_id == user_id:
                if update.status & (
                    ChatUpdate.Status.DISCARDED_CALL |
                    ChatUpdate.Status.BUSY_CALL |
                    ChatUpdate.Status.LEFT_GROUP |
                    ChatUpdate.Status.KICKED
                ):
                    call_ended.set()
            elif isinstance(update, StreamEnded) and update.chat_id == user_id:
                if update.device == Device.MICROPHONE:
                    audio_done.set()

        pytgcalls.add_handler(_on_update)

        try:
            await app.start()
            await pytgcalls.start()

            # play() rings the recipient and automatically starts streaming
            # once they answer. It raises if unanswered within py-tgcalls'
            # internal timeout (~30s).
            log.info("Placing call to user %s …", user_id)
            await pytgcalls.play(user_id, MediaStream(audio_path), CallConfig())

            log.info("Call answered — waiting for audio to finish …")

            # Wait for audio to finish (StreamEnded) or call to end, max 5 min
            done, _ = await asyncio.wait(
                [
                    asyncio.create_task(audio_done.wait()),
                    asyncio.create_task(call_ended.wait()),
                ],
                timeout=300,
                return_when=asyncio.FIRST_COMPLETED,
            )
            if not done:
                log.warning("Audio timed out after 5 min — hanging up anyway")

            log.info("Audio finished — hanging up")
            return True

        finally:
            pytgcalls.remove_handler(_on_update)
            try:
                await pytgcalls.leave_call(user_id)
            except Exception:
                pass
            try:
                await app.stop()
            except Exception:
                pass

    async def start_reauth(self, phone: str, code_future: asyncio.Future) -> str:
        """
        Two-step re-authentication for headless (no-stdin) environments.

        Drives Pyrogram's auth API explicitly so no stdin is needed:
          1. connect() + send_code() → Telegram sends the SMS
          2. Await code_future (resolved when user replies with OTP)
          3. sign_in(phone, phone_code_hash, code) with the actual string

        Returns a result string suitable for sending back to the user.
        """
        from pyrogram import Client

        app = Client(
            self.session_name,
            api_id=self.api_id,
            api_hash=self.api_hash,
            workdir=str(_SESSION_DIR),
        )
        try:
            await app.connect()

            sent = await app.send_code(phone)
            phone_code_hash = sent.phone_code_hash

            # Wait for the user to reply with the OTP (up to 5 minutes)
            code: str = await asyncio.wait_for(code_future, timeout=300)

            await app.sign_in(phone, phone_code_hash, code)
            me = await app.get_me()
            return f"✅ Authenticated as {me.phone_number} (@{me.username})"

        except asyncio.TimeoutError:
            return "❌ Auth timed out — no OTP received within 5 minutes."
        except Exception as e:
            # SessionPasswordNeeded means 2FA is enabled — catch by name to
            # avoid importing an error class that may not exist in all versions.
            if "SessionPasswordNeeded" in type(e).__name__ or "PASSWORD_HASH_INVALID" in str(e):
                return "❌ 2FA password required — not supported in the bot flow yet."
            return f"❌ Auth failed: {e}"
        finally:
            try:
                await app.disconnect()
            except Exception:
                pass
