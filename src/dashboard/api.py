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

_DUBAI_TZ = timezone(timedelta(hours=4))


def _dubai_today() -> date:
    return datetime.now(_DUBAI_TZ).date()
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

# In-memory chat history for the dashboard chat (dashboard user_id = 0)
_chat_history: List[dict] = []
_MAX_HISTORY = 200


# ── helpers ──────────────────────────────────────────────────────────────────

def _app_state(request: Request):
    return request.app.state


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
    state = _app_state(request)
    tg_app = getattr(state, "tg_app", None)
    memory = tg_app.bot_data.get("memory") if tg_app else None
    if not memory:
        return {"files": []}
    memory_dir = memory.workspace / "memory"
    files = []
    for f in sorted(memory_dir.glob("*.md"), reverse=True)[:30]:
        files.append({"name": f.name, "size": f.stat().st_size, "date": f.stem})
    return {"files": files}


@router.get("/memory/today")
async def get_today_log(request: Request):
    state = _app_state(request)
    tg_app = getattr(state, "tg_app", None)
    memory = tg_app.bot_data.get("memory") if tg_app else None
    if not memory:
        return {"date": str(_dubai_today()), "content": ""}
    return {"date": str(_dubai_today()), "content": memory.daily_log()}


@router.get("/memory/{filename}")
async def get_memory_file(request: Request, filename: str):
    state = _app_state(request)
    tg_app = getattr(state, "tg_app", None)
    memory = tg_app.bot_data.get("memory") if tg_app else None
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
    state = _app_state(request)
    tg_app = getattr(state, "tg_app", None)
    memory = tg_app.bot_data.get("memory") if tg_app else None
    ollama = getattr(state, "ollama", None)
    if not memory:
        raise HTTPException(503, "Memory not available")

    learnings = payload.learnings

    if not learnings:
        today_log = memory.daily_log()
        if not today_log:
            raise HTTPException(400, "Nothing to flush — today's log is empty")

        # Try summarising with the agent (Claude); fall back to raw log tail
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
    log_file = Path("/opt/kovo/logs/gateway.log")
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

_WORKSPACE_ROOT = Path("/opt/kovo/workspace")
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

_SETTINGS_PATH = Path("/opt/kovo/config/settings.yaml")
_ENV_PATH = Path("/opt/kovo/config/.env")


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
    """Attempt to restart the miniclaw systemd service."""
    for svc in ("kovo", "kovo.service"):
        try:
            r = subprocess.run(
                ["systemctl", "restart", svc],
                capture_output=True, text=True, timeout=10,
            )
            if r.returncode == 0:
                return {"restarted": True, "service": svc}
        except Exception:
            pass
    return {"restarted": False, "error": "systemctl restart failed — check service name"}


@router.get("/service/status")
async def service_status():
    for svc in ("kovo", "kovo.service"):
        try:
            r = subprocess.run(
                ["systemctl", "is-active", svc],
                capture_output=True, text=True, timeout=5,
            )
            if r.returncode in (0, 3):  # 0=active, 3=inactive
                return {"service": svc, "active": r.returncode == 0, "state": r.stdout.strip()}
        except Exception:
            pass
    return {"service": "unknown", "active": False, "state": "unknown"}


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
        usage = shutil.disk_usage("/opt/kovo")
        info["disk_total_gb"] = round(usage.total / 1e9, 1)
        info["disk_used_gb"] = round(usage.used / 1e9, 1)
        info["disk_free_gb"] = round(usage.free / 1e9, 1)
        info["disk_pct"] = round(usage.used / usage.total * 100, 1)
    except Exception:
        pass
    try:
        mem_info = Path("/proc/meminfo").read_text()
        def _kb(key):
            m = re.search(rf"^{key}:\s+(\d+)", mem_info, re.MULTILINE)
            return int(m.group(1)) * 1024 if m else 0
        total = _kb("MemTotal")
        avail = _kb("MemAvailable")
        info["ram_total_gb"] = round(total / 1e9, 1)
        info["ram_used_gb"] = round((total - avail) / 1e9, 1)
        info["ram_free_gb"] = round(avail / 1e9, 1)
        info["ram_pct"] = round((total - avail) / total * 100, 1) if total else 0
    except Exception:
        pass
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


@router.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for the dashboard chat interface.
    Connects to MiniClaw (user_id=0 for dashboard).
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


# ── Security ──────────────────────────────────────────────────────────────────

_SEC_DIR = Path("/opt/kovo/data/security")
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
    """Trigger the security audit skill via subprocess (non-blocking)."""
    script = Path("/opt/kovo/workspace/skills/security-audit/run.sh")
    if script.exists():
        try:
            subprocess.Popen(
                ["bash", str(script)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return {"started": True}
        except Exception as e:
            return {"started": False, "error": str(e)}
    return {"started": False, "error": "security-audit run.sh not found"}


@router.post("/security/baseline")
async def security_reset_baseline():
    """Reset the security baseline to the current system state."""
    _SEC_DIR.mkdir(parents=True, exist_ok=True)
    entry = {"reset_at": datetime.now().isoformat(), "note": "Baseline reset via dashboard"}
    _SEC_BASELINE.write_text(json.dumps(entry, indent=2))
    return {"reset": True}


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
