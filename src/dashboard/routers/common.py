"""Shared helpers for the dashboard routers."""
from __future__ import annotations

import re

from fastapi import Request

from src.utils.platform import kovo_dir


# Read KOVO version from bootstrap.sh
def _read_version() -> str:
    try:
        bs = (kovo_dir() / "bootstrap.sh").read_text()
        m = re.search(r'KOVO_VERSION="([^"]+)"', bs)
        return m.group(1) if m else "0.0.0"
    except Exception:
        return "0.0.0"

_KOVO_VERSION = _read_version()


# ── helpers ──────────────────────────────────────────────────────────────────

def _app_state(request: Request):
    return request.app.state


def _get_memory(request: Request):
    """Get MemoryManager from app.state or tg_app.bot_data."""
    state = _app_state(request)
    mem = getattr(state, "memory", None)
    if mem:
        return mem
    tg_app = getattr(state, "tg_app", None)
    if tg_app:
        return tg_app.bot_data.get("memory")
    return None

