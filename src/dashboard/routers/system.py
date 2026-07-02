"""
System endpoints — status, metrics, logs, service, storage, ollama.
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


# ── Logs ──────────────────────────────────────────────────────────────────────

@router.get("/logs")
async def get_logs(lines: int = 200):
    lines = min(max(lines, 1), 2000)  # cap to prevent OOM
    log_file = kovo_dir() / "logs" / "gateway.log"
    if not log_file.exists():
        return {"lines": []}
    try:
        all_lines = log_file.read_text(encoding="utf-8", errors="ignore").splitlines()
        return {"lines": all_lines[-lines:]}
    except Exception as e:
        raise HTTPException(500, str(e))


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


# ── Storage purge ─────────────────────────────────────────────────────────────

@router.post("/storage/purge")
async def storage_purge(request: Request):
    """Run tier-1 auto-purge (tmp, audio, screenshots)."""
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
