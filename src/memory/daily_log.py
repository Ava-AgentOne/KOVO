"""
Session-aware daily log helper.
A DailyLogSession accumulates entries during a conversation, then flushes to disk.
"""
from __future__ import annotations
from src.utils.tz import get_tz as _get_tz

import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from src.memory.manager import MemoryManager

log = logging.getLogger(__name__)


class DailyLogSession:
    """Accumulates log entries for a single conversation session."""

    def __init__(self, memory: "MemoryManager", label: str | None = None):
        self.memory = memory
        self.label = label or datetime.now(_get_tz()).strftime("Session %H:%M")
        self._entries: list[str] = []

    def add(self, role: str, text: str, max_len: int = 300) -> None:
        truncated = text[:max_len] + ("…" if len(text) > max_len else "")
        self._entries.append(f"- **{role}**: {truncated}")

    def flush(self) -> None:
        if not self._entries:
            return
        body = "\n".join(self._entries)
        self.memory.append_daily_log(body, session_label=self.label)
        self._entries.clear()
        log.debug("Flushed %d entries to daily log", len(self._entries))

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.flush()
