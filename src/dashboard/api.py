"""
Dashboard REST API — aggregates the per-domain routers under /api/.
The endpoints live in src/dashboard/routers/ (split from the original
single-file api.py in v2.0). Auth is enforced per sub-router.
"""
from fastapi import APIRouter

from src.dashboard.routers import (
    backup, chat, heartbeat, mcp, memory, security, settings, skills,
    system, tools_agents, updates,
)

router = APIRouter()
for _module in (
    system, tools_agents, skills, memory, heartbeat,
    settings, chat, security, backup, updates, mcp,
):
    router.include_router(_module.router)
