"""
Mission Control data (v2.1): live busy state + activity-feed parsing.

The agent marks itself busy while generating a reply (any channel); the
dashboard Overview polls this to show a "Kovo is working on…" indicator.
The activity feed is parsed out of the memory system's daily log, which
every subsystem already writes to — no new event plumbing needed.
"""
from __future__ import annotations

import re

from src.utils.tz import now

# ── Busy state ────────────────────────────────────────────────────────────────

_busy: dict | None = None


def set_busy(user_id: int, message: str) -> None:
    global _busy
    _busy = {
        "channel": "dashboard" if user_id == 0 else "telegram",
        "preview": message.strip().replace("\n", " ")[:80],
        "since": now().isoformat(timespec="seconds"),
    }


def clear_busy() -> None:
    global _busy
    _busy = None


def get_busy() -> dict | None:
    return _busy


# ── Activity feed ─────────────────────────────────────────────────────────────

_ENTRY_RE = re.compile(r"^- \[(\d{2}:\d{2})\]", re.M)
_META_RE = re.compile(r"agent=\S+(\s+model=(\S+))?")


def _classify(text: str) -> str:
    low = text.lower()
    if "reminder" in low:
        return "reminder"
    if "call" in low and ("voice" in low or "phone" in low or "urgent" in low or "made" in low):
        return "call"
    if "alert" in low or "heartbeat" in low or "⚠" in text:
        return "alert"
    if "image" in low and ("sent" in low or "generated" in low):
        return "image"
    if "User:" in text or "Reply:" in text:
        return "chat"
    return "note"


def parse_daily_log(content: str, limit: int = 30) -> list[dict]:
    """Split a daily log into structured feed entries, newest first."""
    if not content:
        return []
    entries = []
    matches = list(_ENTRY_RE.finditer(content))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        body = content[m.end():end].strip()
        meta = _META_RE.search(body)
        model = meta.group(2) if meta and meta.group(2) else None
        body = _META_RE.sub("", body).strip()
        # Prefer the user's message as the summary line for chat entries
        user_m = re.search(r"User:\s*(.+)", body)
        summary = (user_m.group(1) if user_m else body).strip()
        summary = re.sub(r"\s+", " ", summary)
        entries.append({
            "time": m.group(1),
            "type": _classify(body),
            "text": summary[:200],
            "model": model,
        })
    entries.reverse()
    return entries[:limit]
