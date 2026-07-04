"""
KOVO self-update endpoints.
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

# ── Updates ───────────────────────────────────────────────────────────────────

_UPDATE_SCRIPT = kovo_dir() / "scripts" / "update.sh"
_UPDATE_LOG = kovo_dir() / "logs" / "update.log"


@router.get("/update/check")
async def update_check():
    """Check for available KOVO updates."""
    if not _UPDATE_SCRIPT.exists():
        return {"error": "update.sh not found"}
    try:
        result = subprocess.run(
            ["bash", str(_UPDATE_SCRIPT), "--json"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout.strip())
        return {"update_available": False, "error": result.stderr.strip() or "Check failed"}
    except subprocess.TimeoutExpired:
        return {"update_available": False, "error": "Timed out reaching GitHub"}
    except json.JSONDecodeError:
        return {"update_available": False, "error": "Invalid response from update script"}
    except Exception as e:
        return {"update_available": False, "error": str(e)}


@router.post("/update/apply")
async def update_apply():
    """Apply a KOVO update. Runs in background — check /update/log for progress."""
    if not _UPDATE_SCRIPT.exists():
        return {"ok": False, "error": "update.sh not found"}
    try:
        # Run in background so the API can respond immediately
        subprocess.Popen(
            ["bash", str(_UPDATE_SCRIPT), "--apply"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return {"ok": True, "message": "Update started. The service will restart automatically."}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/update/log")
async def update_log(lines: int = 50):
    """Get the update log."""
    if not _UPDATE_LOG.exists():
        return {"lines": []}
    try:
        all_lines = _UPDATE_LOG.read_text(encoding="utf-8", errors="ignore").splitlines()
        return {"lines": all_lines[-lines:]}
    except Exception as e:
        return {"lines": [], "error": str(e)}
