"""
Heartbeat scheduler endpoints.
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

# ── Heartbeat ─────────────────────────────────────────────────────────────────

@router.get("/heartbeat/status")
async def heartbeat_status(request: Request):
    state = _app_state(request)
    tg_app = getattr(state, "tg_app", None)
    heartbeat = tg_app.bot_data.get("heartbeat") if tg_app else None
    if not heartbeat:
        return {"running": False, "jobs": []}

    jobs = []
    for job in heartbeat._scheduler.get_jobs():
        next_run = job.next_run_time
        jobs.append({
            "id": job.id,
            "next_run": next_run.isoformat() if next_run else None,
        })
    return {"running": heartbeat._started, "jobs": jobs}


@router.post("/heartbeat/check")
async def run_health_check(request: Request):
    state = _app_state(request)
    tg_app = getattr(state, "tg_app", None)
    heartbeat = tg_app.bot_data.get("heartbeat") if tg_app else None
    if not heartbeat:
        raise HTTPException(503, "Heartbeat not available")
    report = await heartbeat.run_quick_check_now()
    return {"report": report}


@router.post("/heartbeat/full")
async def run_full_report(request: Request):
    state = _app_state(request)
    tg_app = getattr(state, "tg_app", None)
    heartbeat = tg_app.bot_data.get("heartbeat") if tg_app else None
    if not heartbeat:
        raise HTTPException(503, "Heartbeat not available")
    report = await heartbeat.run_full_report_now()
    return {"report": report}
