"""
MCP server management endpoints (Phase 3d).
List / add / remove / enable external MCP servers, and probe connectivity.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.agents import mcp_config
from src.dashboard.auth import require_auth

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api", dependencies=[Depends(require_auth)])


@router.get("/mcp/servers")
async def mcp_servers():
    """List configured MCP servers (headers masked)."""
    return {"servers": mcp_config.list_servers()}


class McpServerBody(BaseModel):
    name: str
    type: str | None = None          # sse | http | stdio
    url: str | None = None
    command: str | None = None
    args: list[str] | None = None
    headers: dict[str, str] | None = None
    env: dict[str, str] | None = None    # stdio servers; ${VAR} supported
    enabled: bool = True


@router.post("/mcp/servers")
async def add_mcp_server(body: McpServerBody):
    entry: dict = {"enabled": body.enabled}
    if body.type:
        entry["type"] = body.type.strip().lower()
    if body.url:
        entry["url"] = body.url.strip()
    if body.command:
        entry["command"] = body.command.strip()
    if body.args:
        entry["args"] = body.args
    if body.headers:
        entry["headers"] = body.headers
    if body.env:
        entry["env"] = body.env
    try:
        mcp_config.add_server(body.name, entry)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"added": True, "name": body.name}


@router.delete("/mcp/servers/{name}")
async def delete_mcp_server(name: str):
    if not mcp_config.remove_server(name):
        raise HTTPException(404, f"MCP server not found: {name}")
    return {"removed": True, "name": name}


class ToggleBody(BaseModel):
    enabled: bool


@router.post("/mcp/servers/{name}/toggle")
async def toggle_mcp_server(name: str, body: ToggleBody):
    if not mcp_config.set_enabled(name, body.enabled):
        raise HTTPException(404, f"MCP server not found: {name}")
    return {"name": name, "enabled": body.enabled}


@router.post("/mcp/servers/{name}/test")
async def test_mcp_server(name: str):
    """Lightweight reachability probe — no LLM session.

    v2.1: the old probe launched a full SDK query (slow, costly, and flaky —
    max_turns=1 was consumed by the tool call itself, reporting healthy
    servers as unreachable). Now: sse/http servers get a short HTTP request
    (any response = reachable; 401/403 = credentials problem), stdio servers
    a command-on-PATH check.
    """
    # Use the EXPANDED config (cfg.get() resolves ${VAR} from .env) — the raw
    # yaml still holds placeholders and would send "Bearer ${HA_TOKEN}" literally.
    from src.gateway import config as cfg
    entry = (cfg.get().get("mcp") or {}).get(name)
    if not entry:
        raise HTTPException(404, f"MCP server not found: {name}")
    sdk = mcp_config._to_sdk_config(name, entry)
    if sdk is None:
        raise HTTPException(400, "Invalid server config")

    typ = sdk.get("type", "stdio")
    if typ in ("sse", "http"):
        import httpx
        url = sdk.get("url")
        headers = dict(sdk.get("headers") or {})
        if typ == "sse":
            headers.setdefault("Accept", "text/event-stream")
        try:
            async with httpx.AsyncClient(timeout=8, follow_redirects=True) as client:
                # stream() so an SSE endpoint's endless body can't hang us —
                # we only need the status line
                async with client.stream("GET", url, headers=headers) as resp:
                    status = resp.status_code
        except Exception as e:
            log.warning("MCP probe failed for %s: %s", name, e)
            return {"name": name, "reachable": False, "error": str(e)[:200]}
        if status in (401, 403):
            return {"name": name, "reachable": False, "status": status,
                    "error": f"HTTP {status} — check the token"}
        return {"name": name, "reachable": True, "status": status}

    import shutil
    cmd = sdk.get("command")
    found = bool(cmd and shutil.which(cmd))
    return {"name": name, "reachable": found,
            "error": None if found else f"command not found: {cmd}"}
