"""
Cross-platform helpers — detect OS, resolve KOVO_DIR, service commands.

All path resolution flows through kovo_dir(). Every module that previously
hardcoded /opt/kovo should import from here instead.

Supported platforms:
  Linux  — /opt/kovo (default, existing behavior)
  macOS  — ~/.kovo (user-owned, no sudo needed)

The KOVO_DIR environment variable overrides auto-detection on any platform.
"""
from __future__ import annotations

import os
import platform
from pathlib import Path

IS_MACOS = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"


def kovo_dir() -> Path:
    """Return the base KOVO directory for this platform.

    Priority: $KOVO_DIR env var > platform default.
    """
    env = os.environ.get("KOVO_DIR")
    if env:
        return Path(env)
    if IS_MACOS:
        return Path.home() / ".kovo"
    return Path("/opt/kovo")


def workspace_path() -> Path:
    return kovo_dir() / "workspace"


def config_path() -> Path:
    return kovo_dir() / "config"


def data_path() -> Path:
    return kovo_dir() / "data"


def logs_path() -> Path:
    return kovo_dir() / "logs"


def scripts_path() -> Path:
    return kovo_dir() / "scripts"


def venv_python() -> Path:
    return kovo_dir() / "venv" / "bin" / "python"


# ── Service management ───────────────────────────────────────────────────────

_LAUNCHD_LABEL = "com.kovo.agent"


def _launchd_plist() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{_LAUNCHD_LABEL}.plist"


def service_restart_cmd() -> list[str]:
    """Return the shell command to restart the KOVO service."""
    if IS_MACOS:
        plist = _launchd_plist()
        return ["bash", "-c", f"sleep 2 && launchctl unload {plist} 2>/dev/null; launchctl load {plist}"]
    return ["bash", "-c", "sleep 2 && sudo systemctl restart kovo"]


def service_status() -> dict:
    """Check whether the KOVO service is running. Returns {service, active, state}."""
    import subprocess

    if IS_MACOS:
        try:
            r = subprocess.run(
                ["launchctl", "list", _LAUNCHD_LABEL],
                capture_output=True, text=True, timeout=5,
            )
            if r.returncode == 0:
                # Parse PID from launchctl list output
                active = '"PID"' in r.stdout or "PID" in r.stdout.split("\n")[0]
                return {"service": _LAUNCHD_LABEL, "active": active, "state": "active" if active else "inactive"}
            return {"service": _LAUNCHD_LABEL, "active": False, "state": "not loaded"}
        except Exception:
            return {"service": _LAUNCHD_LABEL, "active": False, "state": "unknown"}

    # Linux — try systemctl
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


# ── System info helpers ──────────────────────────────────────────────────────

def get_ram_info() -> dict:
    """Return RAM info dict using psutil (cross-platform)."""
    try:
        import psutil
        vm = psutil.virtual_memory()
        return {
            "ram_total_gb": round(vm.total / 1e9, 1),
            "ram_used_gb": round(vm.used / 1e9, 1),
            "ram_free_gb": round(vm.available / 1e9, 1),
            "ram_pct": round(vm.percent, 1),
        }
    except Exception:
        return {}


def get_disk_info() -> dict:
    """Return disk info for the KOVO directory (cross-platform)."""
    import shutil
    try:
        usage = shutil.disk_usage(str(kovo_dir()))
        return {
            "disk_total_gb": round(usage.total / 1e9, 1),
            "disk_used_gb": round(usage.used / 1e9, 1),
            "disk_free_gb": round(usage.free / 1e9, 1),
            "disk_pct": round(usage.used / usage.total * 100, 1),
        }
    except Exception:
        return {}
