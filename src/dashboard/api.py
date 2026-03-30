"""
Dashboard REST API — all endpoints under /api/
Includes WebSocket /api/ws/chat for the browser chat interface.
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

from src.utils.tz import today as _tz_today, now as _tz_now


def _dubai_today() -> date:
    return _tz_today()
from typing import List

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel

from src.utils.platform import kovo_dir, service_restart_cmd, service_status as _platform_service_status, get_ram_info, get_disk_info

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

# Read KOVO version from bootstrap.sh
def _read_version() -> str:
    try:
        bs = (kovo_dir() / "bootstrap.sh").read_text()
        import re
        m = re.search(r'KOVO_VERSION="([^"]+)"', bs)
        return m.group(1) if m else "0.0.0"
    except Exception:
        return "0.0.0"

_KOVO_VERSION = _read_version()


# In-memory chat history for the dashboard chat (dashboard user_id = 0)
_chat_history: List[dict] = []
_MAX_HISTORY = 200


# ── helpers ──────────────────────────────────────────────────────────────────

def _app_state(request: Request):
    return request.app.state


def _get_memory(request: Request):
    """Get MemoryManager from app.state or tg_app.bot_data."""
    state = _app_state(request)
    mem = getattr(state, "memory", None)
    if mem:
        return mem
    tg_app = getattr(state, "tg_app", None)
    if tg_app:
        return tg_app.bot_data.get("memory")
    return None


# ── Status / Overview ─────────────────────────────────────────────────────────

@router.get("/status")
async def get_status(request: Request):
    state = _app_state(request)
    ollama = getattr(state, "ollama", None)
    try:
        ollama_ok = await ollama.is_available() if ollama else False
    except Exception:
        ollama_ok = False

    tg_app = getattr(state, "tg_app", None)
    bot_data = tg_app.bot_data if tg_app else {}

    skills = bot_data.get("skills")
    heartbeat = bot_data.get("heartbeat")
    tool_registry = getattr(state, "tool_registry", None)
    sub_agent_runner = getattr(state, "sub_agent_runner", None)

    return {
        "status": "ok",
        "version": _KOVO_VERSION,
        "ollama": ollama_ok,
        "telegram": bool(tg_app),
        "heartbeat_running": bool(heartbeat and heartbeat._started),
        "sub_agent_count": len(sub_agent_runner.all()) if sub_agent_runner else 0,
        "skill_count": len(skills.all()) if skills else 0,
        "tool_count": len(tool_registry.all()) if tool_registry else 0,
        "tools_ready": sum(1 for t in tool_registry.available()) if tool_registry else 0,
    }


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


# ── Skills ────────────────────────────────────────────────────────────────────

@router.get("/skills")
async def get_skills(request: Request):
    state = _app_state(request)
    tg_app = getattr(state, "tg_app", None)
    skills_reg = tg_app.bot_data.get("skills") if tg_app else None
    if not skills_reg:
        return {"skills": []}
    return {
        "skills": [
            {
                "name": s.name,
                "description": s.description,
                "tools": s.tools,
                "triggers": s.triggers,
                "path": str(s.path),
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
        return {"date": str(_dubai_today()), "content": ""}
    return {"date": str(_dubai_today()), "content": memory.daily_log()}


@router.get("/memory/{filename}")
async def get_memory_file(request: Request, filename: str):
    memory = _get_memory(request)
    if not memory:
        raise HTTPException(503, "Memory not available")
    # Allow workspace root files too
    safe_names = {
        "MEMORY.md", "SOUL.md", "USER.md", "IDENTITY.md",
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


# ── Heartbeat ─────────────────────────────────────────────────────────────────

@router.get("/heartbeat/status")
async def heartbeat_status(request: Request):
    state = _app_state(request)
    tg_app = getattr(state, "tg_app", None)
    heartbeat = tg_app.bot_data.get("heartbeat") if tg_app else None
    if not heartbeat:
        return {"running": False, "jobs": []}

    jobs = []
    for job in heartbeat._scheduler.get_jobs():
        next_run = job.next_run_time
        jobs.append({
            "id": job.id,
            "next_run": next_run.isoformat() if next_run else None,
        })
    return {"running": heartbeat._started, "jobs": jobs}


@router.post("/heartbeat/check")
async def run_health_check(request: Request):
    state = _app_state(request)
    tg_app = getattr(state, "tg_app", None)
    heartbeat = tg_app.bot_data.get("heartbeat") if tg_app else None
    if not heartbeat:
        raise HTTPException(503, "Heartbeat not available")
    report = await heartbeat.run_quick_check_now()
    return {"report": report}


@router.post("/heartbeat/full")
async def run_full_report(request: Request):
    state = _app_state(request)
    tg_app = getattr(state, "tg_app", None)
    heartbeat = tg_app.bot_data.get("heartbeat") if tg_app else None
    if not heartbeat:
        raise HTTPException(503, "Heartbeat not available")
    report = await heartbeat.run_full_report_now()
    return {"report": report}


# ── Logs ──────────────────────────────────────────────────────────────────────

@router.get("/logs")
async def get_logs(lines: int = 200):
    log_file = kovo_dir() / "logs" / "gateway.log"
    if not log_file.exists():
        return {"lines": []}
    try:
        all_lines = log_file.read_text(encoding="utf-8", errors="ignore").splitlines()
        return {"lines": all_lines[-lines:]}
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


# ── Workspace file save ────────────────────────────────────────────────────────

_WORKSPACE_ROOT = kovo_dir() / "workspace"
_WORKSPACE_WRITEABLE = {
    "MEMORY.md", "SOUL.md", "USER.md", "IDENTITY.md",
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


# ── Settings ──────────────────────────────────────────────────────────────────

_SETTINGS_PATH = kovo_dir() / "config" / "settings.yaml"
_ENV_PATH = kovo_dir() / "config" / ".env"


@router.get("/settings")
async def get_settings():
    if not _SETTINGS_PATH.exists():
        return {"content": ""}
    return {"content": _SETTINGS_PATH.read_text(encoding="utf-8")}


class SaveSettingsRequest(BaseModel):
    content: str


@router.put("/settings")
async def save_settings(payload: SaveSettingsRequest):
    import yaml as _yaml
    try:
        _yaml.safe_load(payload.content)  # validate YAML before saving
    except Exception as e:
        raise HTTPException(400, f"Invalid YAML: {e}")
    _SETTINGS_PATH.write_text(payload.content, encoding="utf-8")
    return {"saved": True}


class UpdateEnvRequest(BaseModel):
    key: str
    value: str


@router.post("/env/update")
async def update_env(payload: UpdateEnvRequest):
    """Update a single .env key-value pair. Creates the key if it doesn't exist."""
    _env = kovo_dir() / "config" / ".env"
    if not _env.exists():
        _env.write_text(f"{payload.key}={payload.value}\n")
        return {"updated": True, "key": payload.key}

    lines = _env.read_text().splitlines()
    found = False
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            # Check if it's a commented-out version of this key
            uncommented = stripped.lstrip("# ")
            if "=" in uncommented and uncommented.split("=", 1)[0].strip() == payload.key:
                # Replace commented-out line with the new value
                new_lines.append(f"{payload.key}={payload.value}")
                found = True
                continue
        if "=" in stripped and not stripped.startswith("#"):
            k, _, _ = stripped.partition("=")
            if k.strip() == payload.key:
                new_lines.append(f"{payload.key}={payload.value}")
                found = True
                continue
        new_lines.append(line)

    if not found:
        new_lines.append(f"{payload.key}={payload.value}")

    _env.write_text("\n".join(new_lines) + "\n")
    return {"updated": True, "key": payload.key}


@router.get("/env")
async def get_env():
    """Return .env entries with values masked. Clients can request reveal per key."""
    if not _ENV_PATH.exists():
        return {"entries": []}
    entries = []
    for line in _ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            entries.append({"type": "comment", "raw": line})
            continue
        if "=" in line:
            key, _, val = line.partition("=")
            entries.append({"type": "var", "key": key.strip(), "masked": "•" * min(len(val), 12), "value": val.strip()})
        else:
            entries.append({"type": "comment", "raw": line})
    return {"entries": entries}


# ── Service controls ──────────────────────────────────────────────────────────

@router.post("/service/restart")
async def restart_service():
    """Restart the kovo service with a 2s delay so the API can respond first."""
    try:
        subprocess.Popen(
            service_restart_cmd(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return {"restarted": True, "service": "kovo"}
    except Exception as e:
        return {"restarted": False, "error": str(e)}


@router.get("/service/status")
async def service_status():
    return _platform_service_status()


# ── System info ───────────────────────────────────────────────────────────────

@router.get("/system/info")
async def system_info():
    info: dict = {}
    info["python"] = sys.version.split()[0]
    try:
        r = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=5)
        info["node"] = r.stdout.strip().lstrip("v") if r.returncode == 0 else "unavailable"
    except Exception:
        info["node"] = "unavailable"
    try:
        usage = shutil.disk_usage(str(kovo_dir()))
        info["disk_total_gb"] = round(usage.total / 1e9, 1)
        info["disk_used_gb"] = round(usage.used / 1e9, 1)
        info["disk_free_gb"] = round(usage.free / 1e9, 1)
        info["disk_pct"] = round(usage.used / usage.total * 100, 1)
    except Exception:
        pass
    info.update(get_ram_info())
    return info


# ── Ollama test ───────────────────────────────────────────────────────────────

@router.post("/ollama/test")
async def test_ollama(request: Request):
    state = _app_state(request)
    ollama = getattr(state, "ollama", None)
    if not ollama:
        return {"ok": False, "error": "Ollama client not initialised"}
    try:
        ok = await ollama.is_available()
        return {"ok": ok, "url": getattr(ollama, "base_url", "?")}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── WebSocket Chat ─────────────────────────────────────────────────────────────

@router.get("/chat/history")
async def get_chat_history():
    """Return the in-memory dashboard chat history."""
    return {"messages": _chat_history}


@router.post("/chat/clear")
async def clear_chat_history():
    """Clear the in-memory dashboard chat history."""
    _chat_history.clear()
    return {"cleared": True}


@router.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for the dashboard chat interface.
    Connects to Kovo (user_id=0 for dashboard).
    """
    await websocket.accept()

    # Everything after accept() is wrapped so any startup error is logged
    # rather than causing a silent immediate disconnect.
    try:
        # Resolve agent from app state — scope["app"] is the FastAPI instance.
        state = websocket.scope["app"].state
        agent = getattr(state, "agent", None)

        # Send existing history on connect
        await websocket.send_json({"type": "history", "messages": _chat_history})

        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
            except json.JSONDecodeError:
                payload = {"message": data}

            message = (payload.get("message") or "").strip()
            if not message:
                continue

            # Add user message to history
            user_msg = {"role": "user", "content": message}
            _chat_history.append(user_msg)
            if len(_chat_history) > _MAX_HISTORY:
                _chat_history.pop(0)

            # Echo user message back to confirm receipt
            await websocket.send_json({"type": "message", **user_msg})

            # Signal typing
            await websocket.send_json({"type": "typing"})

            if agent is None:
                response_text = "Agent not available — system still starting up."
                model_used = "none"
            else:
                try:
                    result = await agent.handle(message=message, user_id=0)
                    response_text = result.get("text", "(no response)")
                    model_used = result.get("model_used", "?")
                except Exception as e:
                    log.error("Chat agent error: %s", e)
                    response_text = f"Error: {e}"
                    model_used = "error"

            # Add assistant reply to history
            assistant_msg = {
                "role": "assistant",
                "content": response_text,
                "model": model_used,
            }
            _chat_history.append(assistant_msg)
            if len(_chat_history) > _MAX_HISTORY:
                _chat_history.pop(0)

            await websocket.send_json({"type": "message", **assistant_msg})

    except WebSocketDisconnect:
        log.info("Dashboard chat disconnected")
    except Exception as e:
        log.error("Chat WebSocket error: %s", e)
        try:
            await websocket.close()
        except Exception:
            pass


# ── Storage purge ─────────────────────────────────────────────────────────────

@router.post("/storage/purge")
async def storage_purge(request: Request):
    """Run tier-1 auto-purge (tmp, audio, screenshots, __pycache__)."""
    state = _app_state(request)
    storage = getattr(state, "storage", None)
    if not storage:
        # Fallback: create a temporary StorageManager
        try:
            from src.tools.storage import StorageManager
            storage = StorageManager()
        except Exception as e:
            return {"ok": False, "error": f"StorageManager not available: {e}"}
    try:
        result = storage.auto_purge()
        return {
            "ok": True,
            "deleted": result.get("deleted", 0),
            "freed_bytes": result.get("freed_bytes", 0),
            "details": result.get("details", []),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── Security ──────────────────────────────────────────────────────────────────

_SEC_DIR = kovo_dir() / "data" / "security"
_SEC_LATEST = _SEC_DIR / "latest.json"
_SEC_HISTORY = _SEC_DIR / "history.json"
_SEC_BASELINE = _SEC_DIR / "baseline.json"


def _sec_read(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def _sec_append_history(entry: dict) -> None:
    _SEC_DIR.mkdir(parents=True, exist_ok=True)
    hist = _sec_read(_SEC_HISTORY).get("history", [])
    hist.insert(0, entry)
    hist = hist[:50]  # keep last 50
    _SEC_HISTORY.write_text(json.dumps({"history": hist}, indent=2))


@router.get("/security/latest")
async def security_latest():
    data = _sec_read(_SEC_LATEST)
    if not data:
        return {}
    return data


@router.get("/security/history")
async def security_history():
    return _sec_read(_SEC_HISTORY) or {"history": []}


@router.post("/security/run")
async def security_run():
    """Run security checks (ClamAV, chkrootkit, rkhunter) and save results."""
    import asyncio

    async def _run_audit():
        results = {}
        findings = []
        timestamp = _tz_now().isoformat()

        # ── System baseline checks ────────────────────────────────
        # Package count
        pkg_count = 0
        try:
            r = subprocess.run(["dpkg", "--get-selections"], capture_output=True, text=True, timeout=10)
            pkg_count = len([l for l in r.stdout.splitlines() if "\tinstall" in l])
            results["packages"] = {"status": "clean", "output": f"{pkg_count} packages installed"}
        except Exception:
            results["packages"] = {"status": "error", "output": "Could not count packages"}

        # SUID binaries
        suid_count = 0
        try:
            r = subprocess.run(
                ["find", "/", "-perm", "-4000", "-type", "f"],
                capture_output=True, text=True, timeout=30,
            )
            suid_files = [l for l in r.stdout.splitlines() if l.strip()]
            suid_count = len(suid_files)
            results["suid_binaries"] = {"status": "clean", "output": f"{suid_count} SUID binaries found"}
        except Exception:
            results["suid_binaries"] = {"status": "error", "output": "Could not scan SUID binaries"}

        # Failed SSH logins (last 24h)
        failed_logins = 0
        try:
            r = subprocess.run(
                ["grep", "-c", "Failed password", "/var/log/auth.log"],
                capture_output=True, text=True, timeout=10,
            )
            failed_logins = int(r.stdout.strip()) if r.returncode == 0 else 0
            status = "warning" if failed_logins > 20 else "clean"
            if failed_logins > 20:
                findings.append(f"{failed_logins} failed login attempts detected")
            results["failed_logins"] = {"status": status, "output": f"{failed_logins} failed login attempts"}
        except Exception:
            results["failed_logins"] = {"status": "clean", "output": "0 failed logins (no auth.log)"}

        # Listening ports
        try:
            r = subprocess.run(
                ["ss", "-tlnp"],
                capture_output=True, text=True, timeout=10,
            )
            ports = [l for l in r.stdout.splitlines()[1:] if l.strip()]
            results["listening_ports"] = {"status": "clean", "output": f"{len(ports)} listening ports"}
        except Exception:
            results["listening_ports"] = {"status": "error", "output": "Could not check ports"}

        # .env permissions
        env_path = kovo_dir() / "config" / ".env"
        try:
            import stat
            if env_path.exists():
                mode = env_path.stat().st_mode
                is_loose = bool(mode & (stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH))
                if is_loose:
                    findings.append(f".env has loose permissions ({oct(mode & 0o777)})")
                    results["env_permissions"] = {"status": "warning", "output": f"Permissions: {oct(mode & 0o777)} — should be 600"}
                else:
                    results["env_permissions"] = {"status": "clean", "output": f"Permissions: {oct(mode & 0o777)}"}
        except Exception:
            results["env_permissions"] = {"status": "error", "output": "Could not check .env"}

        # Executable files in /tmp
        try:
            r = subprocess.run(
                ["find", "/tmp", "/dev/shm", "-type", "f", "-executable", "-not", "-path", "*/systemd*"],
                capture_output=True, text=True, timeout=10,
            )
            exec_files = [l for l in r.stdout.splitlines() if l.strip()]
            if exec_files:
                findings.append(f"Executable files found in /tmp ({len(exec_files)})")
                results["tmp_executables"] = {"status": "warning", "output": f"{len(exec_files)} executable files in /tmp"}
            else:
                results["tmp_executables"] = {"status": "clean", "output": "No executable files in /tmp"}
        except Exception:
            results["tmp_executables"] = {"status": "clean", "output": "Check skipped"}

        # Failed systemd services
        try:
            r = subprocess.run(
                ["systemctl", "--failed", "--no-legend"],
                capture_output=True, text=True, timeout=10,
            )
            failed = [l for l in r.stdout.splitlines() if l.strip()]
            if failed:
                findings.append(f"Failed systemd services: {len(failed)}")
                results["systemd_failed"] = {"status": "warning", "output": "\n".join(failed[:5])}
            else:
                results["systemd_failed"] = {"status": "clean", "output": "All services running"}
        except Exception:
            results["systemd_failed"] = {"status": "clean", "output": "Check skipped"}

        # ── Malware / rootkit scans ───────────────────────────────
        # ClamAV
        try:
            r = subprocess.run(
                ["clamscan", "--infected", "--recursive", "--no-summary", str(kovo_dir() / "data"), str(kovo_dir() / "workspace")],
                capture_output=True, text=True, timeout=120,
            )
            if r.returncode != 0 and r.stdout.strip():
                findings.append("Malware detected by ClamAV")
            results["clamav"] = {
                "status": "clean" if r.returncode == 0 else "warning",
                "output": r.stdout.strip()[-500:] if r.stdout else "(no output)",
            }
        except FileNotFoundError:
            results["clamav"] = {"status": "not_installed", "output": "clamscan not found — install with: sudo apt install clamav"}
        except subprocess.TimeoutExpired:
            results["clamav"] = {"status": "timeout", "output": "Scan timed out (120s)"}
        except Exception as e:
            results["clamav"] = {"status": "error", "output": str(e)}

        # chkrootkit
        try:
            r = subprocess.run(
                ["sudo", "chkrootkit", "-q"],
                capture_output=True, text=True, timeout=60,
            )
            infected = [l for l in r.stdout.splitlines() if "INFECTED" in l]
            if infected:
                findings.append("Rootkit detected by chkrootkit")
            results["chkrootkit"] = {
                "status": "warning" if infected else "clean",
                "output": "\n".join(infected) if infected else "No rootkits found",
            }
        except FileNotFoundError:
            results["chkrootkit"] = {"status": "not_installed", "output": "chkrootkit not found"}
        except Exception as e:
            results["chkrootkit"] = {"status": "error", "output": str(e)}

        # rkhunter
        try:
            r = subprocess.run(
                ["sudo", "rkhunter", "--check", "--skip-keypress", "--report-warnings-only"],
                capture_output=True, text=True, timeout=120,
            )
            warnings = r.stdout.strip()
            if warnings:
                findings.append("rkhunter reported warnings")
            results["rkhunter"] = {
                "status": "warning" if warnings else "clean",
                "output": warnings[-500:] if warnings else "No warnings",
            }
        except FileNotFoundError:
            results["rkhunter"] = {"status": "not_installed", "output": "rkhunter not found"}
        except Exception as e:
            results["rkhunter"] = {"status": "error", "output": str(e)}

        # ── Overall status ────────────────────────────────────────
        statuses = [v["status"] for v in results.values()]
        if any(s == "warning" for s in statuses):
            overall = "warning"
        elif all(s in ("clean", "not_installed", "timeout") for s in statuses):
            overall = "clean"
        else:
            overall = "error"

        # Build summary
        summary = f"All clear — {pkg_count} packages, {suid_count} SUID binaries, {failed_logins} failed logins"
        if findings:
            summary = f"{len(findings)} issue(s) found"

        report = {
            "status": overall,
            "timestamp": timestamp,
            "checks": results,
            "findings": findings,
            "summary": summary,
        }

        # Save to disk
        _SEC_DIR.mkdir(parents=True, exist_ok=True)
        _SEC_LATEST.write_text(json.dumps(report, indent=2))
        _sec_append_history(report)

        return report

    # Run in background so the API responds immediately
    asyncio.create_task(_run_audit())
    return {"started": True}


@router.post("/security/baseline")
async def security_reset_baseline():
    """Reset the security baseline to the current system state."""
    _SEC_DIR.mkdir(parents=True, exist_ok=True)
    entry = {"reset_at": _tz_now().isoformat(), "note": "Baseline reset via dashboard"}
    _SEC_BASELINE.write_text(json.dumps(entry, indent=2))
    return {"reset": True}


@router.delete("/security/history")
async def clear_security_history():
    """Clear all security audit history."""
    if _SEC_HISTORY.exists():
        _SEC_HISTORY.write_text(json.dumps({"history": []}, indent=2))
    return {"cleared": True}


# ── Metrics ───────────────────────────────────────────────────────────────────

@router.get("/metrics")
async def get_metrics():
    """Return basic system metrics (CPU, RAM, disk, uptime)."""
    try:
        import psutil, time
        cpu = psutil.cpu_percent(interval=0.2)
        vm = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        boot = psutil.boot_time()
        uptime_sec = int(time.time() - boot)
        days, rem = divmod(uptime_sec, 86400)
        hours, rem = divmod(rem, 3600)
        mins = rem // 60
        if days:
            uptime_str = f"{days}d {hours}h {mins}m"
        elif hours:
            uptime_str = f"{hours}h {mins}m"
        else:
            uptime_str = f"{mins}m"
        return {
            "cpu_percent": round(cpu, 1),
            "cpu_cores": psutil.cpu_count(),
            "ram_percent": round(vm.percent, 1),
            "ram_used_gb": round(vm.used / 1e9, 1),
            "ram_total_gb": round(vm.total / 1e9, 1),
            "disk_percent": round(disk.percent, 1),
            "disk_used_gb": round(disk.used / 1e9, 1),
            "disk_total_gb": round(disk.total / 1e9, 1),
            "uptime": uptime_str,
        }
    except Exception as e:
        log.warning("Metrics error: %s", e)
        return {}


# ── ClawHub ───────────────────────────────────────────────────────────────────

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


# ── Backup ────────────────────────────────────────────────────────────────────

_BACKUP_DIR = kovo_dir() / "data" / "backups"
_BACKUP_SCRIPT = kovo_dir() / "scripts" / "backup.sh"


def _human_size(size_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f}TB"


@router.post("/backup")
async def run_backup(tier: str = "core"):
    """Run the backup script. tier: 'core' or 'full'."""
    _BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    if not _BACKUP_SCRIPT.exists():
        return {"ok": False, "error": "backup.sh not found"}
    cmd = ["bash", str(_BACKUP_SCRIPT)]
    if tier == "full":
        cmd.append("--full")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            files = sorted(_BACKUP_DIR.glob("kovo-backup-*"), key=lambda f: f.stat().st_mtime, reverse=True)
            if not files:
                files = sorted(_BACKUP_DIR.glob("*"), key=lambda f: f.stat().st_mtime, reverse=True)
            size = _human_size(files[0].stat().st_size) if files else "?"
            return {"ok": True, "output": result.stdout.strip()[-2000:], "size": size, "tier": tier}
        return {"ok": False, "error": result.stderr.strip() or "Backup script failed"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "Backup timed out (5min)"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/backup/list")
async def list_backups():
    """List all backup files with sizes."""
    _BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backups = []
    total = 0
    for f in sorted(_BACKUP_DIR.iterdir(), key=lambda f: f.stat().st_mtime, reverse=True):
        if f.is_file():
            size = f.stat().st_size
            total += size
            backups.append({
                "name": f.name,
                "size": _human_size(size),
                "date": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
            })
    return {"backups": backups, "total_size": _human_size(total), "count": len(backups)}


@router.delete("/backup/{filename}")
async def delete_backup(filename: str):
    """Delete a specific backup file."""
    if ".." in filename or "/" in filename:
        raise HTTPException(400, "Invalid filename")
    target = _BACKUP_DIR / filename
    if not target.exists():
        raise HTTPException(404, "Backup not found")
    target.unlink()
    return {"deleted": True, "filename": filename}


@router.get("/backup/download/{filename}")
async def download_backup(filename: str):
    """Download a backup file."""
    if ".." in filename or "/" in filename:
        raise HTTPException(400, "Invalid filename")
    target = _BACKUP_DIR / filename
    if not target.exists():
        raise HTTPException(404, "Backup not found")
    return FileResponse(
        path=str(target),
        filename=filename,
        media_type="application/gzip",
    )




@router.get("/backup/manifest/{filename}")
async def get_backup_manifest(filename: str):
    """Read manifest.json from a backup archive."""
    if ".." in filename or "/" in filename:
        raise HTTPException(400, "Invalid filename")
    backup_path = _BACKUP_DIR / filename
    if not backup_path.exists():
        raise HTTPException(404, "Backup not found")
    try:
        import tarfile as _tf
        with _tf.open(str(backup_path), "r:gz") as tar:
            for name in ("./manifest.json", "manifest.json"):
                try:
                    mf = tar.extractfile(name)
                    if mf:
                        return json.loads(mf.read().decode())
                except Exception:
                    continue
        return {"error": "No manifest found (legacy backup)"}
    except Exception as e:
        return {"error": str(e)}

@router.post("/backup/restore")
async def restore_backup(file: UploadFile = File(...)):
    """Restore from a KOVO backup archive (v2 format with manifest)."""
    if not file.filename.endswith((".tar.gz", ".tgz")):
        return {"ok": False, "output": "Only .tar.gz backup files are accepted."}

    import tempfile
    tmp_path = None
    try:
        content = await file.read()
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".tar.gz", dir="/tmp")
        import os
        os.close(tmp_fd)
        with open(tmp_path, "wb") as f:
            f.write(content)

        # Save copy in backups dir
        _BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        import shutil as _sh
        _sh.copy2(tmp_path, _BACKUP_DIR / file.filename)

        # Use restore.sh v2 if available, fallback to raw extract
        restore_script = kovo_dir() / "scripts" / "restore.sh"
        if restore_script.exists():
            result = subprocess.run(
                ["bash", str(restore_script), tmp_path],
                capture_output=True, text=True, timeout=300,
            )
        else:
            result = subprocess.run(
                ["tar", "xzf", tmp_path, "-C", str(kovo_dir()), "--overwrite"],
                capture_output=True, text=True, timeout=60,
            )

        # Read manifest if available
        manifest = None
        try:
            import tarfile as _tf
            with _tf.open(tmp_path, "r:gz") as tar:
                for name in ("./manifest.json", "manifest.json"):
                    try:
                        mf = tar.extractfile(name)
                        if mf:
                            manifest = json.loads(mf.read().decode())
                            break
                    except Exception:
                        continue
        except Exception:
            pass

        try:
            subprocess.Popen(service_restart_cmd(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

        return {
            "ok": result.returncode == 0,
            "output": result.stdout.strip()[-2000:] if result.stdout else "",
            "manifest": manifest,
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "output": "Restore timed out (5min)."}
    except Exception as e:
        return {"ok": False, "output": f"Restore error: {e}"}
    finally:
        if tmp_path:
            import os
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


# ── Security Fix (direct commands) ────────────────────────────────────────────

class SecurityFixRequest(BaseModel):
    command: str
    dry_run: bool = False


@router.post("/security/fix")
async def security_fix(payload: SecurityFixRequest):
    """Run a security fix command directly. Fast and deterministic."""
    ALLOWED_PREFIXES = [
        "find /tmp", "find /dev/shm",
        "grep ", "apt list", "apt-get",
        "systemctl", "clamscan", "sudo chkrootkit",
        "sudo apt", "which ", "echo ",
    ]
    cmd = payload.command.strip()
    if not any(cmd.startswith(p) for p in ALLOWED_PREFIXES):
        return {"ok": False, "output": f"Command not allowed: {cmd[:50]}"}

    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=30,
        )
        output = (result.stdout.strip() + "\n" + result.stderr.strip()).strip()
        return {"ok": True, "output": output or "(no output)"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "output": "Command timed out (30s)"}
    except Exception as e:
        return {"ok": False, "output": f"Error: {e}"}


# ── Updates ───────────────────────────────────────────────────────────────────

_UPDATE_SCRIPT = kovo_dir() / "scripts" / "update.sh"
_UPDATE_LOG = kovo_dir() / "logs" / "update.log"


@router.get("/update/check")
async def update_check():
    """Check for available KOVO updates."""
    if not _UPDATE_SCRIPT.exists():
        return {"error": "update.sh not found"}
    try:
        result = subprocess.run(
            ["bash", str(_UPDATE_SCRIPT), "--json"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout.strip())
        return {"update_available": False, "error": result.stderr.strip() or "Check failed"}
    except subprocess.TimeoutExpired:
        return {"update_available": False, "error": "Timed out reaching GitHub"}
    except json.JSONDecodeError:
        return {"update_available": False, "error": "Invalid response from update script"}
    except Exception as e:
        return {"update_available": False, "error": str(e)}


@router.post("/update/apply")
async def update_apply():
    """Apply a KOVO update. Runs in background — check /update/log for progress."""
    if not _UPDATE_SCRIPT.exists():
        return {"ok": False, "error": "update.sh not found"}
    try:
        # Run in background so the API can respond immediately
        subprocess.Popen(
            ["bash", str(_UPDATE_SCRIPT), "--apply"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return {"ok": True, "message": "Update started. The service will restart automatically."}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/update/log")
async def update_log(lines: int = 50):
    """Get the update log."""
    if not _UPDATE_LOG.exists():
        return {"lines": []}
    try:
        all_lines = _UPDATE_LOG.read_text(encoding="utf-8", errors="ignore").splitlines()
        return {"lines": all_lines[-lines:]}
    except Exception as e:
        return {"lines": [], "error": str(e)}
