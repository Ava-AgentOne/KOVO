"""
Add-ons (v3.0 Phase 3.5) — guided companion setup for the dashboard.

The MCP Store pattern applied to system-level companions: each add-on is a
catalog entry with live status (not_installed → installed → ready) and
guided install/configure flows. Every install's exact commands are shown
to the owner BEFORE running (the dashboard confirms first), commands are
fixed server-side strings (never user input), and installs run in a
background thread with a tailable log.

v1 targets Linux (the reference deployment). On other platforms the cards
show manual instructions via the docs link.
"""
from __future__ import annotations

import asyncio
import logging
import platform
import shutil
import subprocess
import threading

log = logging.getLogger(__name__)

IS_LINUX = platform.system() == "Linux"

# ── Install command sets (fixed, shown to the owner before running) ──────────

TAILSCALE_INSTALL = [
    'sh -c \'curl -fsSL "https://pkgs.tailscale.com/stable/ubuntu/$(lsb_release -cs).noarmor.gpg" | sudo tee /usr/share/keyrings/tailscale-archive-keyring.gpg >/dev/null\'',
    'sh -c \'curl -fsSL "https://pkgs.tailscale.com/stable/ubuntu/$(lsb_release -cs).tailscale-keyring.list" | sudo tee /etc/apt/sources.list.d/tailscale.list >/dev/null\'',
    "sudo apt-get update -qq",
    "sudo apt-get install -y tailscale",
    "sudo systemctl enable --now tailscaled",
]

OLLAMA_INSTALL = [
    "sh -c 'curl -fsSL https://ollama.com/install.sh | sh'",
]

# ── Install job state (one at a time, tailable log) ──────────────────────────

_job: dict = {"addon": None, "state": "idle", "log": []}
_job_lock = threading.Lock()


def job_status() -> dict:
    with _job_lock:
        return {"addon": _job["addon"], "state": _job["state"],
                "log": list(_job["log"])[-40:]}


def _run_install(addon_id: str, commands: list[str]) -> None:
    with _job_lock:
        _job.update(addon=addon_id, state="running", log=[])
    ok = True
    for cmd in commands:
        with _job_lock:
            _job["log"].append(f"$ {cmd}")
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True,
                               text=True, timeout=600)
            tail = (r.stdout + r.stderr).strip().splitlines()[-6:]
            with _job_lock:
                _job["log"].extend(tail)
            if r.returncode != 0:
                ok = False
                with _job_lock:
                    _job["log"].append(f"[exit {r.returncode}] — stopping")
                break
        except Exception as e:
            ok = False
            with _job_lock:
                _job["log"].append(f"[error] {e}")
            break
    with _job_lock:
        _job["state"] = "done" if ok else "failed"
    log.info("Add-on install %s: %s", addon_id, _job["state"])


def start_install(addon_id: str) -> dict:
    """Kick off a background install. Returns the commands being run."""
    entry = get(addon_id)
    if not entry:
        raise ValueError(f"Unknown add-on: {addon_id}")
    commands = entry.get("install_commands") or []
    if not commands:
        raise ValueError(f"Add-on {addon_id} has no automated install here "
                         "— see its docs for manual steps.")
    with _job_lock:
        if _job["state"] == "running":
            raise ValueError("Another install is already running.")
    threading.Thread(target=_run_install, args=(addon_id, commands),
                     daemon=True).start()
    return {"started": True, "commands": commands}


# ── Detection ─────────────────────────────────────────────────────────────────

def _detect_tailscale() -> dict:
    if not shutil.which("tailscale"):
        return {"status": "not_installed"}
    try:
        r = subprocess.run(["tailscale", "status", "--json"],
                           capture_output=True, text=True, timeout=5)
        import json
        st = json.loads(r.stdout or "{}")
        if st.get("BackendState") == "Running":
            self_info = st.get("Self") or {}
            ips = self_info.get("TailscaleIPs") or []
            dns = (self_info.get("DNSName") or "").rstrip(".")
            return {"status": "ready",
                    "detail": f"on tailnet — {dns or (ips[0] if ips else '?')}",
                    "extra": {"dns": dns, "ip": ips[0] if ips else None}}
        return {"status": "installed",
                "detail": f"installed, not connected ({st.get('BackendState', 'stopped')})"}
    except Exception:
        return {"status": "installed", "detail": "installed, state unknown"}


def _detect_google() -> dict:
    from src.utils.platform import config_path
    creds = config_path() / "google-credentials.json"
    token = config_path() / "google-token.json"
    if not creds.exists():
        return {"status": "not_installed",
                "detail": "no OAuth credentials file"}
    if not token.exists():
        return {"status": "installed", "detail": "credentials present — sign-in needed"}
    try:
        import json
        scopes = json.loads(token.read_text()).get("scopes") or []
        n = len(scopes)
        return {"status": "ready", "detail": f"connected ({n} scopes)"}
    except Exception:
        return {"status": "installed", "detail": "token unreadable — re-auth"}


def _detect_ollama() -> dict:
    import httpx
    from src.gateway import config as cfg
    binary = shutil.which("ollama") is not None
    try:
        r = httpx.get(cfg.ollama_url().rstrip("/") + "/api/tags", timeout=3)
        models = [m.get("name") for m in r.json().get("models", [])]
        if models:
            return {"status": "ready",
                    "detail": f"{len(models)} model(s): {', '.join(models[:3])}"}
        return {"status": "installed", "detail": "running, no models pulled yet"}
    except Exception:
        pass
    if binary:
        return {"status": "installed", "detail": "installed, service not reachable"}
    return {"status": "not_installed"}


def _detect_home_assistant() -> dict:
    from src.gateway import config as cfg
    mcp = cfg.get().get("mcp") or {}
    if "home_assistant" in mcp:
        return {"status": "ready", "detail": "connected via MCP"}
    return {"status": "not_installed", "detail": "add it from the MCP Store"}


# ── Catalog ───────────────────────────────────────────────────────────────────

def catalog() -> list[dict]:
    return [
        {
            "id": "tailscale",
            "label": "Tailscale",
            "desc": "Reach the dashboard from anywhere — private encrypted "
                    "network between your devices, zero open ports.",
            "category": "network",
            "install_commands": TAILSCALE_INSTALL if IS_LINUX else None,
            "configure_kind": "tailscale",   # auth-link + join polling
            "docs": "https://tailscale.com/kb/1031/install-linux",
        },
        {
            "id": "google_workspace",
            "label": "Google Workspace",
            "desc": "Gmail, Drive, Docs, Calendar — plus nightly off-site "
                    "backups to your Drive.",
            "category": "integration",
            "install_commands": None,        # config-only: upload + OAuth
            "configure_kind": "google",      # credentials upload + consent link
            "docs": "https://developers.google.com/workspace/guides/create-credentials",
        },
        {
            "id": "ollama",
            "label": "Ollama (local LLM)",
            "desc": "Free local model for heartbeat summaries and cheap tasks "
                    "— nothing leaves your machine.",
            "category": "ai",
            "install_commands": OLLAMA_INSTALL if IS_LINUX else None,
            "configure_kind": "ollama",      # pull a model
            "docs": "https://ollama.com/download",
        },
        {
            "id": "home_assistant",
            "label": "Home Assistant",
            "desc": "Control your smart home in natural language via the "
                    "MCP integration.",
            "category": "integration",
            "install_commands": None,
            "configure_kind": "link",        # hands off to /integrations Store
            "link": "/integrations",
            "docs": "https://www.home-assistant.io/integrations/mcp_server/",
        },
    ]


_DETECTORS = {
    "tailscale": _detect_tailscale,
    "google_workspace": _detect_google,
    "ollama": _detect_ollama,
    "home_assistant": _detect_home_assistant,
}


def get(addon_id: str) -> dict | None:
    return next((a for a in catalog() if a["id"] == addon_id), None)


def list_with_status() -> list[dict]:
    out = []
    for entry in catalog():
        e = dict(entry)
        try:
            e.update(_DETECTORS[entry["id"]]())
        except Exception as ex:
            e.update(status="unknown", detail=str(ex)[:80])
        e["installable"] = bool(entry.get("install_commands"))
        e.pop("install_commands", None)   # UI fetches them on demand
        out.append(e)
    return out


# ── Configure flows ───────────────────────────────────────────────────────────

_ts_proc: asyncio.subprocess.Process | None = None


async def tailscale_login_url() -> dict:
    """Run `tailscale up` detached and capture the auth URL it prints."""
    global _ts_proc
    if _detect_tailscale()["status"] == "ready":
        return {"already": True}
    proc = await asyncio.create_subprocess_exec(
        "sudo", "-n", "tailscale", "up",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
    )
    _ts_proc = proc
    url = None
    try:
        async with asyncio.timeout(20):
            while True:
                line = (await proc.stdout.readline()).decode()
                if not line:
                    break
                if "https://login.tailscale.com/" in line:
                    url = line.strip()
                    break
    except TimeoutError:
        pass
    if not url:
        return {"error": "no auth URL from tailscale (already authorized? "
                         "check status)"}
    return {"auth_url": url}


_google_flow = None


def google_auth_start() -> dict:
    global _google_flow
    from src.tools.google_api import start_auth_flow
    url, flow = start_auth_flow()
    _google_flow = flow
    return {"auth_url": url}


def google_auth_complete(code_or_url: str) -> dict:
    global _google_flow
    if _google_flow is None:
        raise ValueError("Start the Google sign-in first.")
    from src.tools.google_api import complete_auth_flow
    result = complete_auth_flow(_google_flow, code_or_url)
    if result.startswith("✅"):
        _google_flow = None
        return {"ok": True, "message": result}
    return {"ok": False, "message": result}


def ollama_pull(model: str) -> dict:
    """Pull a model in the background via the install-job machinery."""
    import re
    model = model.strip()
    if not re.fullmatch(r"[\w.:\-/]{1,80}", model):
        raise ValueError("Invalid model name.")
    with _job_lock:
        if _job["state"] == "running":
            raise ValueError("Another install is already running.")
    threading.Thread(target=_run_install,
                     args=("ollama", [f"ollama pull {model}"]),
                     daemon=True).start()
    return {"started": True, "model": model}
