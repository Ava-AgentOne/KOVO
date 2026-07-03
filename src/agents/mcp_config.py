"""
External MCP servers (Phase 3d) — connect KOVO to third-party tool servers.

settings.yaml:
  mcp:
    home_assistant:
      type: sse
      url: http://10.0.1.20:8123/mcp_server/sse
      headers:
        Authorization: "Bearer ${HA_TOKEN}"
    github:
      type: http
      url: https://api.githubcopilot.com/mcp/
      headers:
        Authorization: "Bearer ${GITHUB_TOKEN}"
    filesystem:
      command: npx
      args: ["-y", "@modelcontextprotocol/server-filesystem", "/data"]
      enabled: false

Each entry becomes an mcp_servers[name] passed to the Agent SDK, alongside
KOVO's in-process `kovo` tools. `${VAR}` placeholders (typically bearer
tokens in headers) are resolved from the environment by config._expand.
`enabled: false` skips a server without deleting its config. Only the SDK
brain uses these — the CLI brain has no tool support.

Server-building reads the EXPANDED config (cfg.get); dashboard CRUD reads
and writes the RAW settings.yaml so `${VAR}` placeholders survive edits.
"""
from __future__ import annotations

import logging

from src.utils.platform import kovo_dir

log = logging.getLogger(__name__)

_SETTINGS_FILE = kovo_dir() / "config" / "settings.yaml"

# Keys the SDK understands per transport; everything else (enabled, notes…) is
# KOVO metadata and must be stripped before handing config to the SDK.
_SDK_KEYS = {
    "stdio": {"type", "command", "args", "env"},
    "sse": {"type", "url", "headers"},
    "http": {"type", "url", "headers"},
}


def _server_type(entry: dict) -> str:
    t = str(entry.get("type", "")).strip().lower()
    if t in ("sse", "http", "stdio"):
        return t
    # Back-compat: an entry with `command` and no type is stdio.
    return "stdio" if entry.get("command") else ""


def _to_sdk_config(name: str, entry: dict) -> dict | None:
    """Strip KOVO metadata, keep only valid SDK keys for the transport."""
    if not isinstance(entry, dict):
        return None
    t = _server_type(entry)
    if not t:
        log.warning("MCP server %r has no valid type/command — skipped", name)
        return None
    allowed = _SDK_KEYS[t]
    cfg = {k: v for k, v in entry.items() if k in allowed}
    if t == "stdio":
        cfg.setdefault("type", "stdio")
        if not cfg.get("command"):
            log.warning("MCP stdio server %r missing command — skipped", name)
            return None
    else:
        cfg["type"] = t
        if not cfg.get("url"):
            log.warning("MCP %s server %r missing url — skipped", t, name)
            return None
    return cfg


def external_servers() -> dict:
    """Return {name: sdk_config} for enabled external MCP servers (expanded)."""
    from src.gateway import config as cfg
    raw = cfg.get().get("mcp") or {}
    if not isinstance(raw, dict):
        return {}
    out = {}
    for name, entry in raw.items():
        if not isinstance(entry, dict) or entry.get("enabled") is False:
            continue
        sdk = _to_sdk_config(name, entry)
        if sdk is not None:
            out[name] = sdk
    return out


def external_allowed_tools(names=None) -> list[str]:
    """Allow all tools from each enabled server via the `mcp__<name>` prefix."""
    if names is None:
        names = external_servers().keys()
    return [f"mcp__{n}" for n in names]


# ── Dashboard CRUD (operates on RAW settings.yaml) ───────────────────────────

def _read_raw() -> dict:
    import yaml
    if not _SETTINGS_FILE.exists():
        return {}
    return yaml.safe_load(_SETTINGS_FILE.read_text()) or {}


def _write_raw(data: dict) -> None:
    import yaml
    _SETTINGS_FILE.write_text(yaml.safe_dump(data, sort_keys=False, default_flow_style=False))
    from src.gateway import config as cfg
    cfg.reload()


def _mask_headers(headers: dict) -> dict:
    """Hide secret-ish header values for display (keeps ${VAR} placeholders visible)."""
    masked = {}
    for k, v in (headers or {}).items():
        s = str(v)
        if s.startswith("${") and s.endswith("}"):
            masked[k] = s  # placeholder is not a secret
        elif len(s) > 8:
            masked[k] = s[:4] + "…" + s[-2:]
        else:
            masked[k] = "•••"
    return masked


def list_servers() -> list[dict]:
    """Server list for the dashboard — headers masked, secrets never returned."""
    raw = _read_raw().get("mcp") or {}
    servers = []
    for name, entry in raw.items():
        if not isinstance(entry, dict):
            continue
        servers.append({
            "name": name,
            "type": _server_type(entry) or "?",
            "enabled": entry.get("enabled", True) is not False,
            "url": entry.get("url"),
            "command": entry.get("command"),
            "args": entry.get("args"),
            "headers": _mask_headers(entry.get("headers", {})),
        })
    return servers


def add_server(name: str, entry: dict) -> None:
    """Create/replace a server entry. Validated as an SDK config first."""
    name = name.strip()
    if not name or not name.replace("_", "").replace("-", "").isalnum():
        raise ValueError("Server name must be alphanumeric (plus _ or -).")
    if _to_sdk_config(name, entry) is None:
        raise ValueError("Invalid server config: need type sse/http + url, or command for stdio.")
    data = _read_raw()
    data.setdefault("mcp", {})[name] = entry
    _write_raw(data)
    log.info("MCP server %r added/updated", name)


def remove_server(name: str) -> bool:
    data = _read_raw()
    mcp = data.get("mcp") or {}
    if name not in mcp:
        return False
    del mcp[name]
    _write_raw(data)
    log.info("MCP server %r removed", name)
    return True


def set_enabled(name: str, enabled: bool) -> bool:
    data = _read_raw()
    mcp = data.get("mcp") or {}
    if name not in mcp or not isinstance(mcp[name], dict):
        return False
    mcp[name]["enabled"] = enabled
    _write_raw(data)
    log.info("MCP server %r enabled=%s", name, enabled)
    return True
