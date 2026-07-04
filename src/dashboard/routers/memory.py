"""
Memory files and workspace file endpoints.
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

# ── Memory ────────────────────────────────────────────────────────────────────

@router.get("/memory/files")
async def list_memory_files(request: Request):
    memory = _get_memory(request)
    if not memory:
        return {"files": []}
    memory_dir = memory.workspace / "memory"
    files = []
    for f in sorted(memory_dir.glob("*.md"), reverse=True)[:30]:
        files.append({"name": f.name, "size": f.stat().st_size, "date": f.stem})
    return {"files": files}


@router.get("/memory/today")
async def get_today_log(request: Request):
    memory = _get_memory(request)
    if not memory:
        return {"date": str(_tz_today()), "content": ""}
    return {"date": str(_tz_today()), "content": memory.daily_log()}


@router.get("/memory/{filename}")
async def get_memory_file(request: Request, filename: str):
    memory = _get_memory(request)
    if not memory:
        raise HTTPException(503, "Memory not available")
    # Allow workspace root files too
    safe_names = {
        "MEMORY.md", "SOUL.md", "USER.md",
        "AGENTS.md", "TOOLS.md", "HEARTBEAT.md",
    }
    if filename in safe_names:
        path = memory.workspace / filename
    else:
        path = memory.workspace / "memory" / filename
    if not path.exists():
        raise HTTPException(404, f"File not found: {filename}")
    return {"filename": filename, "content": path.read_text(encoding="utf-8")}


class FlushRequest(BaseModel):
    learnings: str = ""


@router.post("/memory/flush")
async def flush_memory(request: Request, payload: FlushRequest):
    memory = _get_memory(request)
    if not memory:
        raise HTTPException(503, "Memory not available")

    learnings = payload.learnings

    if not learnings:
        today_log = memory.daily_log()
        if not today_log:
            return {"flushed": False, "error": "Nothing to flush — today's log is empty. Send some messages first."}

        # Try summarising with the agent (Claude); fall back to raw log tail
        state = _app_state(request)
        agent = getattr(state, "agent", None)
        if agent:
            try:
                result = await agent.handle(
                    message=(
                        "Summarise the key learnings and facts from today's agent log "
                        "in 3-5 concise bullet points. Focus on decisions made, "
                        "problems solved, and information worth remembering.\n\n"
                        f"{today_log[-2000:]}"
                    ),
                    user_id=0,
                    force_complexity="medium",
                )
                learnings = result.get("text", "").strip()
            except Exception as e:
                log.warning("Agent summarisation failed during flush: %s", e)
                learnings = ""

        if not learnings:
            # Plain fallback — store the raw tail so the button always works
            learnings = today_log[-800:].strip()

    memory.flush_to_memory(learnings)
    return {"flushed": True, "learnings": learnings[:500]}


# ── Workspace file save ────────────────────────────────────────────────────────

_WORKSPACE_ROOT = kovo_dir() / "workspace"
_WORKSPACE_WRITEABLE = {
    "MEMORY.md", "SOUL.md", "USER.md",
    "AGENTS.md", "TOOLS.md", "HEARTBEAT.md",
}


class SaveFileRequest(BaseModel):
    content: str


@router.get("/workspace/{filepath:path}")
async def get_workspace_file(filepath: str):
    """Read a file from the workspace (same path rules as PUT)."""
    if ".." in filepath or filepath.startswith("/"):
        raise HTTPException(400, "Invalid file path")
    target = _WORKSPACE_ROOT / filepath
    try:
        target.resolve().relative_to(_WORKSPACE_ROOT.resolve())
    except ValueError:
        raise HTTPException(403, "Path outside workspace")
    if not target.exists():
        raise HTTPException(404, f"File not found: {filepath}")
    return {"filepath": filepath, "content": target.read_text(encoding="utf-8")}


@router.put("/workspace/{filepath:path}")
async def save_workspace_file(filepath: str, payload: SaveFileRequest):
    """Save a file within the workspace. Accepts workspace root files and memory/*.md."""
    # Prevent path traversal
    if ".." in filepath or filepath.startswith("/"):
        raise HTTPException(400, "Invalid file path")
    target = _WORKSPACE_ROOT / filepath
    # Must be within workspace
    try:
        target.resolve().relative_to(_WORKSPACE_ROOT.resolve())
    except ValueError:
        raise HTTPException(403, "Path outside workspace")
    # Allow workspace root whitelisted files + anything under memory/
    parts = Path(filepath).parts
    if len(parts) == 1:
        if filepath not in _WORKSPACE_WRITEABLE:
            raise HTTPException(403, f"File not editable: {filepath}")
    elif parts[0] != "memory":
        raise HTTPException(403, "Only workspace root files and memory/ logs are editable")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(payload.content, encoding="utf-8")
    return {"saved": True, "filepath": filepath}
