"""
DashboardChannel — the dashboard web chat as a Channel (Phase 3e).

Outbound messages (heartbeat alerts, reminders when selected as the
default surface) are appended to the chat history and pushed live to any
connected WebSocket clients. chat_id is ignored — the dashboard is a
single-owner surface.
"""
from __future__ import annotations

import logging

from src.channels.base import STREAMING, Channel

log = logging.getLogger(__name__)


class DashboardChannel(Channel):
    name = "dashboard"
    capabilities = frozenset({STREAMING})

    async def send_text(self, chat_id, text: str, markdown: bool = True) -> None:
        if not text:
            return
        from src.dashboard.routers import chat
        await chat.broadcast_assistant(text, model="system")
