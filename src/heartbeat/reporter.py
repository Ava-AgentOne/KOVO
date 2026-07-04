"""
Heartbeat reporter — sends health alerts and reports to the owner via the
owner's preferred channel (Phase 3e: channel-agnostic; was Telegram-only).
Optionally logs every check to the structured SQLite store.
"""
from __future__ import annotations

import logging

log = logging.getLogger(__name__)


class HeartbeatReporter:
    def __init__(self, channel, owner_user_id: int, structured_store=None):
        """channel: a src.channels Channel (chunking is the channel's job)."""
        self._channel = channel
        self._uid = owner_user_id
        self._store = structured_store

    async def send(self, text: str, parse_mode: str = "Markdown") -> None:
        """Send a message to the owner via the configured channel."""
        if not text:
            return
        try:
            await self._channel.send_text(
                self._uid, text, markdown=(parse_mode == "Markdown")
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
        await self.send(f"🌅 *Good Morning!*\n\n{briefing}")

    async def send_sim_reminder(self) -> None:
        await self.send(
            "📱 *SIM Top-Up Reminder*\n\n"
            "Your prepaid SIM is approaching 90 days without a top-up. "
            "Top it up soon to keep the Kovo caller account active.\n\n"
            "UAE prepaid SIMs expire after 90 days of no activity."
        )
