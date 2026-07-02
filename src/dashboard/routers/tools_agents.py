"""
Tool registry and sub-agent endpoints.
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

# ── Tools ─────────────────────────────────────────────────────────────────────

@router.get("/tools")
async def get_tools(request: Request):
    state = _app_state(request)
    tool_registry = getattr(state, "tool_registry", None)
    if not tool_registry:
        return {"tools": []}
    return {
        "tools": [
            {
                "name": t.name,
                "status": t.status,
                "description": t.description,
                "available": t.available,
                "install_command": t.install_command,
                "config_needed": t.config_needed,
            }
            for t in tool_registry.all()
        ]
    }


class InstallToolRequest(BaseModel):
    name: str


@router.post("/tools/{name}/install")
async def install_tool(request: Request, name: str):
    """Mark a tool as installed (after manual install) and update TOOLS.md."""
    state = _app_state(request)
    tool_registry = getattr(state, "tool_registry", None)
    if not tool_registry:
        raise HTTPException(503, "Tool registry not available")
    t = tool_registry.get(name)
    if not t:
        raise HTTPException(404, f"Tool not found: {name}")
    tool_registry.update_status(name, "installed")
    return {"updated": True, "name": name, "status": "installed"}


# ── Agents (sub-agents) ───────────────────────────────────────────────────────

@router.get("/agents")
async def get_agents(request: Request):
    state = _app_state(request)
    sub_agent_runner = getattr(state, "sub_agent_runner", None)
    if not sub_agent_runner:
        return {"main_agent": "kovo", "sub_agents": []}
    return {
        "main_agent": "kovo",
        "sub_agents": [
            {
                "name": a.name,
                "purpose": a.purpose,
                "tools": a.tools,
                "soul_preview": a.soul[:300] + "…" if len(a.soul) > 300 else a.soul,
            }
            for a in sub_agent_runner.all()
        ],
    }


class CreateSubAgentRequest(BaseModel):
    name: str
    soul: str
    tools: list[str] = []
    purpose: str = ""


@router.post("/agents")
async def create_sub_agent(request: Request, payload: CreateSubAgentRequest):
    state = _app_state(request)
    sub_agent_runner = getattr(state, "sub_agent_runner", None)
    if not sub_agent_runner:
        raise HTTPException(503, "Sub-agent runner not available")
    try:
        agent = sub_agent_runner.create(
            name=payload.name,
            soul_content=payload.soul,
            tools=payload.tools,
            purpose=payload.purpose,
        )
        return {"created": True, "name": agent.name}
    except Exception as e:
        raise HTTPException(500, str(e))


# ── Tools — edit ──────────────────────────────────────────────────────────────

class UpdateToolRequest(BaseModel):
    status: str | None = None
    config_needed: str | None = None
    description: str | None = None


@router.put("/tools/{name}")
async def update_tool(request: Request, name: str, payload: UpdateToolRequest):
    """Update tool fields (status, config_needed, description) in TOOLS.md."""
    state = _app_state(request)
    tool_registry = getattr(state, "tool_registry", None)
    if not tool_registry:
        raise HTTPException(503, "Tool registry not available")
    t = tool_registry.get(name)
    if not t:
        raise HTTPException(404, f"Tool not found: {name}")
    fields = {k: v for k, v in payload.dict().items() if v is not None}
    tool_registry.update_tool(name, **fields)
    return {"updated": True, "name": name}
