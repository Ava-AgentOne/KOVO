"""
Skill registry and ClawHub marketplace endpoints.
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

# ── Skills ────────────────────────────────────────────────────────────────────

@router.get("/skills")
async def get_skills(request: Request):
    state = _app_state(request)
    tg_app = getattr(state, "tg_app", None)
    skills_reg = tg_app.bot_data.get("skills") if tg_app else None
    if not skills_reg:
        return {"skills": []}
    learner = getattr(state, "learner", None)
    learned = learner.learned_names() if learner else set()
    return {
        "skills": [
            {
                "name": s.name,
                "description": s.description,
                "tools": s.tools,
                "triggers": s.triggers,
                "path": str(s.path),
                "learned": s.name in learned,
            }
            for s in skills_reg.all()
        ]
    }


@router.post("/skills/reload")
async def reload_skills(request: Request):
    """Reload skill registry from disk without restarting the service."""
    state = _app_state(request)
    tg_app = getattr(state, "tg_app", None)
    skills_reg = tg_app.bot_data.get("skills") if tg_app else None
    if not skills_reg:
        return {"ok": False, "error": "skill registry not available"}
    skills_reg.reload()
    return {"ok": True, "count": len(skills_reg.all()), "names": skills_reg.names()}


class CreateSkillRequest(BaseModel):
    name: str
    description: str
    tools: list[str] = []
    triggers: list[str]
    body: str


@router.post("/skills")
async def create_skill(request: Request, payload: CreateSkillRequest):
    state = _app_state(request)
    tg_app = getattr(state, "tg_app", None)
    creator = tg_app.bot_data.get("creator") if tg_app else None
    if not creator:
        raise HTTPException(503, "Skill creator not available")
    try:
        skill = creator.create(
            name=payload.name,
            description=payload.description,
            tools=payload.tools,
            triggers=payload.triggers,
            body=payload.body,
        )
        return {"created": True, "skill": {"name": skill.name, "triggers": skill.triggers}}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.delete("/skills/{name}")
async def delete_skill(request: Request, name: str):
    state = _app_state(request)
    tg_app = getattr(state, "tg_app", None)
    creator = tg_app.bot_data.get("creator") if tg_app else None
    if not creator:
        raise HTTPException(503, "Skill creator not available")
    deleted = creator.delete(name)
    return {"deleted": deleted}


# ── ClawHub ───────────────────────────────────────────────────────────────────

@router.get("/skills/pending")
async def pending_skills(request: Request):
    """Skill proposals awaiting owner approval (v3.0 auto-learning)."""
    learner = getattr(_app_state(request), "learner", None)
    if learner is None:
        return {"pending": []}
    import json as _json
    out = []
    for p in learner.pending():
        p["triggers"] = _json.loads(p["triggers"])
        out.append(p)
    return {"pending": out}


@router.post("/skills/pending/{pid}/approve")
async def approve_pending_skill(request: Request, pid: int):
    learner = getattr(_app_state(request), "learner", None)
    if learner is None:
        raise HTTPException(503, "Skill learning not available")
    try:
        skill = learner.approve(pid)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return {"approved": True, "name": skill.name}


@router.post("/skills/pending/{pid}/reject")
async def reject_pending_skill(request: Request, pid: int):
    learner = getattr(_app_state(request), "learner", None)
    if learner is None:
        raise HTTPException(503, "Skill learning not available")
    if not learner.reject(pid):
        raise HTTPException(404, "Proposal not found or already decided")
    return {"rejected": True}


@router.get("/skills/clawhub/search")
async def clawhub_search(q: str = ""):
    """Search ClawHub skill marketplace via CLI."""
    if not shutil.which("clawhub"):
        return {"error": "clawhub CLI not installed", "results": []}
    try:
        out = subprocess.check_output(
            ["clawhub", "search", q, "--json"],
            timeout=10,
        )
        data = json.loads(out)
        return {"results": data if isinstance(data, list) else data.get("results", [])}
    except subprocess.TimeoutExpired:
        return {"error": "clawhub search timed out", "results": []}
    except subprocess.CalledProcessError as e:
        return {"error": f"clawhub error: {e}", "results": []}
    except Exception as e:
        return {"error": str(e), "results": []}


class _ClawHubInstallReq(BaseModel):
    name: str


@router.post("/skills/clawhub/install")
async def clawhub_install(body: _ClawHubInstallReq, request: Request):
    if not shutil.which("clawhub"):
        return {"ok": False, "error": "clawhub CLI not installed"}
    try:
        subprocess.check_call(
            ["clawhub", "install", body.name],
            timeout=30,
        )
        # Reload skill registry
        state = _app_state(request)
        tg_app = getattr(state, "tg_app", None)
        if tg_app:
            skills = tg_app.bot_data.get("skills")
            if skills and hasattr(skills, "reload"):
                skills.reload()
        return {"ok": True}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "Install timed out"}
    except subprocess.CalledProcessError as e:
        return {"ok": False, "error": f"clawhub error: {e}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
