"""
Heartbeat reporter — sends health alerts and reports to Esam via Telegram.
Optionally logs every check to the structured SQLite store.
"""
from __future__ import annotations

import logging

from telegram.ext import Application

log = logging.getLogger(__name__)

# Max Telegram message length
_MAX_LEN = 4096


class HeartbeatReporter:
    def __init__(self, tg_app: Application, esam_user_id: int, structured_store=None):
        self._app = tg_app
        self._uid = esam_user_id
        self._store = structured_store

    async def send(self, text: str, parse_mode: str = "Markdown") -> None:
        """Send a message to Esam. Splits if >4096 chars."""
        if not text:
            return
        try:
            for i in range(0, len(text), _MAX_LEN):
                await self._app.bot.send_message(
                    chat_id=self._uid,
                    text=text[i : i + _MAX_LEN],
                    parse_mode=parse_mode,
                )
        except Exception as e:
            log.error("Failed to send heartbeat message: %s", e)

    async def send_alert(self, message: str, alerts: list[str] | None = None) -> None:
        log.warning("ALERT: %s", message[:200])
        if self._store:
            self._store.log_heartbeat("alert", "alert", alerts or [message[:200]])
        await self.send(f"🚨 *Alert*\n{message}")

    async def send_health_report(self, report: str, title: str = "Health Report") -> None:
        if self._store:
            self._store.log_heartbeat("full", "ok")
        await self.send(f"📊 *{title}*\n\n{report}")

    async def send_morning_briefing(self, briefing: str) -> None:
        await self.send(f"🌅 *Good Morning, Esam!*\n\n{briefing}")

    async def send_sim_reminder(self) -> None:
        await self.send(
            "📱 *SIM Top-Up Reminder*\n\n"
            "Your prepaid SIM is approaching 90 days without a top-up. "
            "Top it up soon to keep the MiniClaw caller account active.\n\n"
            "UAE prepaid SIMs expire after 90 days of no activity."
        )
