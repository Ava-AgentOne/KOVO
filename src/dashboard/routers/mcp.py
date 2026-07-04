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


# ── Live MCP Registry (v2.1 Store) ────────────────────────────────────────────

_REGISTRY_URL = "https://registry.modelcontextprotocol.io/v0/servers"


def _slug(text: str) -> str:
    import re
    return re.sub(r"[^a-z0-9_]+", "_", text.lower()).strip("_")


def _normalize_registry_entry(item: dict) -> dict | None:
    """Flatten an official-registry entry into the Store card/install shape.

    Prefers a remote (sse/http) endpoint; falls back to an npm/pypi/oci
    package as a stdio command. Returns None for entries KOVO can't run.
    """
    import re
    srv = item.get("server") or {}
    name = srv.get("name") or ""
    label = srv.get("title") or name.split("/")[-1]
    out = {
        "id": _slug(name.split("/")[-1]),
        "label": label,
        "publisher": name,
        "version": srv.get("version"),
        "desc": (srv.get("description") or "")[:200],
        "docs": (srv.get("repository") or {}).get("url") or srv.get("websiteUrl"),
        "source": "registry",
    }

    remotes = srv.get("remotes") or []
    if remotes:
        remote = remotes[0]
        rtype = remote.get("type", "")
        out["type"] = "sse" if rtype == "sse" else "http"
        out["url"] = remote.get("url")
        headers, needs = {}, []
        for h in remote.get("headers") or []:
            hname = h.get("name")
            if not hname:
                continue
            value = h.get("value") or ""
            # Registry uses {var} templates; KOVO uses ${VAR} from .env
            value = re.sub(r"\{(\w+)\}", lambda m: "${" + m.group(1).upper() + "}", value)
            if not value and (h.get("isSecret") or h.get("isRequired")):
                value = "${" + _slug(hname).upper() + "}"
            headers[hname] = value
            if h.get("isRequired"):
                needs.append(f"{hname} header — {h.get('description') or 'credential'}")
        if headers:
            out["headers"] = headers
        if needs:
            out["needs"] = "; ".join(needs)[:200]
        return out if out["url"] else None

    packages = srv.get("packages") or []
    packages = sorted(packages, key=lambda p: {"npm": 0, "pypi": 1}.get(p.get("registryType"), 2))
    for pkg in packages:
        rtype = pkg.get("registryType")
        ident = pkg.get("identifier")
        if not ident or (pkg.get("transport") or {}).get("type", "stdio") != "stdio":
            continue
        run_args = [a.get("value") for a in pkg.get("runtimeArguments") or [] if a.get("value")]
        if rtype == "npm":
            out["command"] = pkg.get("runtimeHint") or "npx"
            out["args"] = (run_args or ["-y"]) + [ident]
        elif rtype == "pypi":
            out["command"] = pkg.get("runtimeHint") or "uvx"
            out["args"] = run_args + [ident]
        elif rtype == "oci":
            out["command"] = "docker"
            out["args"] = ["run", "-i", "--rm", ident]
        else:
            continue
        out["type"] = "stdio"
        env, needs = {}, []
        for ev in pkg.get("environmentVariables") or []:
            evname = ev.get("name")
            if not evname:
                continue
            if ev.get("isRequired") or ev.get("isSecret"):
                env[evname] = "${" + evname + "}"
            if ev.get("isRequired"):
                needs.append(f"{evname} — {ev.get('description') or 'required'}")
        if env:
            out["env"] = env
        if needs:
            out["needs"] = "; ".join(needs)[:200]
        return out
    return None


@router.get("/mcp/registry")
async def search_registry(q: str = "", cursor: str | None = None):
    """Search the official MCP registry (community-published entries)."""
    import httpx
    params: dict = {"limit": 30, "version": "latest"}
    if q.strip():
        params["search"] = q.strip()
    if cursor:
        params["cursor"] = cursor
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(_REGISTRY_URL, params=params)
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        log.warning("MCP registry search failed: %s", e)
        return {"ok": False, "error": str(e)[:200], "servers": []}
    seen: set = set()
    servers = []
    for item in data.get("servers", []):
        norm = _normalize_registry_entry(item)
        if norm and norm["id"] not in seen:
            seen.add(norm["id"])
            servers.append(norm)
    return {
        "ok": True,
        "servers": servers,
        "next_cursor": (data.get("metadata") or {}).get("nextCursor"),
    }


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
