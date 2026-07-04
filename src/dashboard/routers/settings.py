"""
settings.yaml and .env endpoints.
Split from the original src/dashboard/api.py (v2.0).
"""
from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.dashboard.auth import require_auth
from src.dashboard.routers.common import _KOVO_VERSION, _app_state, _get_memory
from src.utils.platform import kovo_dir, service_restart_cmd, service_status as _platform_service_status, get_ram_info, get_disk_info
from src.utils.tz import today as _tz_today, now as _tz_now

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api", dependencies=[Depends(require_auth)])

# ── Settings ──────────────────────────────────────────────────────────────────

_SETTINGS_PATH = kovo_dir() / "config" / "settings.yaml"
_ENV_PATH = kovo_dir() / "config" / ".env"


@router.get("/settings")
async def get_settings():
    if not _SETTINGS_PATH.exists():
        return {"content": ""}
    return {"content": _SETTINGS_PATH.read_text(encoding="utf-8")}


class SaveSettingsRequest(BaseModel):
    content: str


@router.put("/settings")
async def save_settings(payload: SaveSettingsRequest):
    import yaml as _yaml
    try:
        _yaml.safe_load(payload.content)  # validate YAML before saving
    except Exception as e:
        raise HTTPException(400, f"Invalid YAML: {e}")
    _SETTINGS_PATH.write_text(payload.content, encoding="utf-8")
    # Invalidate cached config so get() re-reads from disk
    try:
        from src.gateway.config import reload as _reload_config
        _reload_config()
    except Exception:
        pass
    return {"saved": True}


class UpdateEnvRequest(BaseModel):
    key: str
    value: str


# Keys that can be written via the dashboard — blocks LD_PRELOAD, PATH, etc.
_ALLOWED_ENV_KEYS = {
    "TELEGRAM_BOT_TOKEN", "OWNER_TELEGRAM_ID", "WEBHOOK_URL",
    "TELEGRAM_API_ID", "TELEGRAM_API_HASH",
    "GROQ_API_KEY", "GITHUB_TOKEN",
    "CLAUDE_CODE_OAUTH_TOKEN", "GOOGLE_CREDENTIALS_PATH",
}


@router.post("/env/update")
async def update_env(payload: UpdateEnvRequest):
    """Update a single .env key-value pair. Creates the key if it doesn't exist."""
    key = payload.key.strip().upper()
    if key not in _ALLOWED_ENV_KEYS:
        raise HTTPException(403, f"Key not allowed: {key}. Only KOVO configuration keys can be set via the dashboard.")
    _env = kovo_dir() / "config" / ".env"
    if not _env.exists():
        _env.write_text(f"{key}={payload.value}\n")
        return {"updated": True, "key": key}

    lines = _env.read_text().splitlines()
    found = False
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            # Check if it's a commented-out version of this key
            uncommented = stripped.lstrip("# ")
            if "=" in uncommented and uncommented.split("=", 1)[0].strip() == key:
                # Replace commented-out line with the new value
                new_lines.append(f"{key}={payload.value}")
                found = True
                continue
        if "=" in stripped and not stripped.startswith("#"):
            k, _, _ = stripped.partition("=")
            if k.strip() == key:
                new_lines.append(f"{key}={payload.value}")
                found = True
                continue
        new_lines.append(line)

    if not found:
        new_lines.append(f"{key}={payload.value}")

    _env.write_text("\n".join(new_lines) + "\n")
    return {"updated": True, "key": key}


@router.get("/env")
async def get_env():
    """Return .env entries with values masked. Use POST /api/env/reveal to get actual values."""
    if not _ENV_PATH.exists():
        return {"entries": []}
    entries = []
    for line in _ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            entries.append({"type": "comment", "raw": line})
            continue
        if "=" in line:
            key, _, val = line.partition("=")
            val = val.strip()
            has_value = bool(val) and not val.startswith("#")
            entries.append({"type": "var", "key": key.strip(), "masked": "•" * min(len(val), 12), "has_value": has_value})
        else:
            entries.append({"type": "comment", "raw": line})
    return {"entries": entries}


class RevealEnvRequest(BaseModel):
    key: str


@router.post("/env/reveal")
async def reveal_env(payload: RevealEnvRequest):
    """Return the actual value of a single .env key. Separated from GET to avoid bulk exposure."""
    if not _ENV_PATH.exists():
        raise HTTPException(404, ".env not found")
    for line in _ENV_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("#") or "=" not in stripped:
            continue
        k, _, v = stripped.partition("=")
        if k.strip() == payload.key:
            return {"key": payload.key, "value": v.strip()}
    raise HTTPException(404, f"Key not found: {payload.key}")
