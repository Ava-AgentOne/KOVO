"""
Mission Control endpoints (v2.1) — the data behind the Overview page:
live busy state, activity feed, metrics history, and reminders.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from src.dashboard import activity
from src.dashboard.auth import require_auth
from src.dashboard.metrics_history import history as _metrics_history
from src.dashboard.routers.common import _get_memory

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api", dependencies=[Depends(require_auth)])


@router.get("/activity/busy")
async def get_busy():
    """Whether Kovo is generating a reply right now (any channel)."""
    return {"busy": activity.get_busy()}


@router.get("/activity/recent")
async def get_recent_activity(request: Request):
    """Structured feed entries parsed from today's daily log, newest first."""
    memory = _get_memory(request)
    if not memory:
        return {"entries": []}
    return {"entries": activity.parse_daily_log(memory.daily_log())}


@router.get("/metrics/history")
async def get_metrics_history():
    """Rolling 24h CPU/RAM/disk samples for the sparklines."""
    return {"samples": _metrics_history.samples()}


@router.get("/reminders")
async def list_reminders(request: Request):
    """All pending reminders (single-owner system — no per-user filter)."""
    reminders = getattr(request.app.state, "reminders", None)
    if reminders is None:
        return {"reminders": []}
    return {"reminders": reminders.list_all_pending()}


@router.delete("/reminders/{reminder_id}")
async def cancel_reminder(request: Request, reminder_id: int):
    reminders = getattr(request.app.state, "reminders", None)
    if reminders is None:
        raise HTTPException(503, "Reminders not available")
    if not reminders.cancel_any(reminder_id):
        raise HTTPException(404, "Reminder not found or not pending")
    return {"cancelled": True, "id": reminder_id}
