"""
Routines endpoints (v3.0 Phase 1) — manage recurring autonomous tasks.
"""
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from src.dashboard.auth import require_auth

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api", dependencies=[Depends(require_auth)])


def _mgr(request: Request):
    mgr = getattr(request.app.state, "routines", None)
    if mgr is None:
        raise HTTPException(503, "Routines not available")
    return mgr


@router.get("/routines")
async def list_routines(request: Request):
    return {"routines": _mgr(request).list_all()}


class RoutineBody(BaseModel):
    name: str
    prompt: str
    cron: str
    schedule_text: str = ""
    delivery: str = "message"    # message | silent


@router.post("/routines")
async def create_routine(request: Request, body: RoutineBody):
    from src.gateway import config as cfg
    owner = cfg.allowed_users()[0]
    try:
        rid = _mgr(request).create(
            owner, body.name, body.prompt, body.cron,
            schedule_text=body.schedule_text, delivery=body.delivery,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"created": True, "id": rid}


class ToggleBody(BaseModel):
    enabled: bool


@router.post("/routines/{rid}/toggle")
async def toggle_routine(request: Request, rid: int, body: ToggleBody):
    if not _mgr(request).set_enabled(rid, body.enabled):
        raise HTTPException(404, "Routine not found")
    return {"id": rid, "enabled": body.enabled}


@router.delete("/routines/{rid}")
async def delete_routine(request: Request, rid: int):
    if not _mgr(request).delete(rid):
        raise HTTPException(404, "Routine not found")
    return {"deleted": True, "id": rid}


@router.post("/routines/{rid}/run")
async def run_routine_now(request: Request, rid: int):
    """Fire a routine immediately (doesn't change its schedule)."""
    r = _mgr(request).get(rid)
    if not r:
        raise HTTPException(404, "Routine not found")
    heartbeat = getattr(request.app.state, "heartbeat", None)
    if heartbeat is None:
        raise HTTPException(503, "Scheduler not available")
    asyncio.create_task(heartbeat._run_routine(r))
    return {"started": True, "id": rid}


@router.get("/routines/{rid}/runs")
async def routine_runs(request: Request, rid: int):
    return {"runs": _mgr(request).runs(rid, limit=10)}
