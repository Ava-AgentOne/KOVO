"""
TelegramChannel — the Telegram surface as a Channel (Phase 3e).

Owns the python-telegram-bot Application lifecycle (built via the existing
src/telegram/bot.py machinery, which remains the implementation guts of
this channel) and implements the outbound Channel contract with Telegram's
rules: 4096-char chunking and Markdown-with-plain-fallback.
"""
from __future__ import annotations

import logging
import os

from src.channels.base import BUTTONS, CALLS, PHOTOS, STREAMING, VOICE, Channel

log = logging.getLogger(__name__)

_MAX_LEN = 4096


class TelegramChannel(Channel):
    name = "telegram"
    capabilities = frozenset({STREAMING, PHOTOS, VOICE, BUTTONS, CALLS})

    def __init__(self, **build_kwargs):
        """build_kwargs are forwarded to src.telegram.bot.build_application."""
        from src.telegram.bot import build_application
        self.app = build_application(**build_kwargs)

    @property
    def bot(self):
        return self.app.bot

    # ── lifecycle (moved out of gateway/main.py) ─────────────────────────

    async def start(self) -> None:
        webhook_url = os.environ.get("WEBHOOK_URL", "").strip()
        await self.app.initialize()
        if webhook_url:
            await self.app.bot.set_webhook(
                url=f"{webhook_url}/webhook",
                allowed_updates=["message", "callback_query"],
            )
            await self.app.start()
            log.info("Telegram webhook registered at %s/webhook", webhook_url)
        else:
            log.info("No WEBHOOK_URL — starting long-polling mode")
            await self.app.start()
            await self.app.updater.start_polling(drop_pending_updates=True)
            log.info("Telegram polling started")

    async def stop(self) -> None:
        if self.app.updater and self.app.updater.running:
            await self.app.updater.stop()
        await self.app.stop()
        await self.app.shutdown()

    # ── outbound ──────────────────────────────────────────────────────────

    async def send_text(self, chat_id, text: str, markdown: bool = True) -> None:
        if not text:
            return
        from telegram.error import BadRequest
        for i in range(0, len(text), _MAX_LEN):
            chunk = text[i: i + _MAX_LEN]
            if markdown:
                try:
                    await self.bot.send_message(chat_id=chat_id, text=chunk, parse_mode="Markdown")
                    continue
                except BadRequest:
                    pass  # unbalanced markers — fall through to plain
            await self.bot.send_message(chat_id=chat_id, text=chunk)

    async def send_photo(self, chat_id, path: str, caption: str = "") -> None:
        with open(path, "rb") as fh:
            await self.bot.send_photo(
                chat_id=chat_id, photo=fh, caption=caption[:1024],
                read_timeout=30, write_timeout=60, connect_timeout=15,
            )

    async def send_voice(self, chat_id, path: str, caption: str = "") -> None:
        with open(path, "rb") as fh:
            await self.bot.send_voice(
                chat_id=chat_id, voice=fh, caption=caption[:1024] or None,
                read_timeout=30, write_timeout=60, connect_timeout=15,
            )
