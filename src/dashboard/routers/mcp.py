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
    """Probe a server: launch a tiny SDK session listing its tools."""
    servers = mcp_config.external_servers()
    if name not in servers:
        # Might be disabled — build just this one from raw config
        raw = mcp_config._read_raw().get("mcp", {}).get(name)
        if not raw:
            raise HTTPException(404, f"MCP server not found: {name}")
        sdk = mcp_config._to_sdk_config(name, raw)
        if sdk is None:
            raise HTTPException(400, "Invalid server config")
        servers = {name: sdk}

    try:
        import asyncio
        from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query
        from src.utils.platform import kovo_dir

        async def _probe():
            opts = ClaudeAgentOptions(
                model="haiku",
                mcp_servers={name: servers[name]},
                allowed_tools=[f"mcp__{name}"],
                max_turns=1,
                cwd=str(kovo_dir()),
            )
            ok = False
            async for msg in query(
                prompt=f"List the tools available from the '{name}' server, then stop.",
                options=opts,
            ):
                if isinstance(msg, ResultMessage):
                    ok = not msg.is_error
            return ok

        ok = await asyncio.wait_for(_probe(), timeout=45)
        return {"name": name, "reachable": ok}
    except Exception as e:
        log.warning("MCP test failed for %s: %s", name, e)
        return {"name": name, "reachable": False, "error": str(e)[:200]}
