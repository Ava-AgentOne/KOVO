"""
Security audit, tool install, and fix endpoints.
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
                ["find", "/usr", "/bin", "/sbin", "/lib", "-perm", "-4000", "-type", "f"],
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


# ── Security Tools Install ─────────────────────────────────────────

_INSTALL_LOG = kovo_dir() / "logs" / "security-install.log"
_INSTALL_LOCK = kovo_dir() / "logs" / ".security-install-running"


@router.get("/security/tools-status")
async def security_tools_status():
    """Check which security tools are installed."""
    import shutil
    installing = _INSTALL_LOCK.exists()
    log_content = ""
    if _INSTALL_LOG.exists():
        try:
            log_content = _INSTALL_LOG.read_text(encoding="utf-8", errors="ignore")[-2000:]
        except Exception:
            pass
    return {
        "clamav": bool(shutil.which("clamscan")),
        "chkrootkit": bool(shutil.which("chkrootkit")),
        "rkhunter": bool(shutil.which("rkhunter")),
        "installing": installing,
        "log": log_content if installing else "",
    }


@router.post("/security/install-tools")
async def security_install_tools():
    """Install ClamAV, chkrootkit, and rkhunter in the background."""
    import asyncio

    if _INSTALL_LOCK.exists():
        return {"ok": False, "error": "Installation already in progress"}

    async def _install():
        _INSTALL_LOCK.touch()
        _INSTALL_LOG.parent.mkdir(parents=True, exist_ok=True)
        try:
            # Install each tool separately so one failure doesn't block others
            tools = [
                ("chkrootkit", ["sudo", "DEBIAN_FRONTEND=noninteractive", "apt-get", "install", "-y", "-qq", "--no-install-recommends", "chkrootkit"]),
                ("rkhunter", ["sudo", "DEBIAN_FRONTEND=noninteractive", "apt-get", "install", "-y", "-qq", "--no-install-recommends", "rkhunter"]),
                ("clamav", ["sudo", "DEBIAN_FRONTEND=noninteractive", "apt-get", "install", "-y", "-qq", "--no-install-recommends", "clamav"]),
            ]
            with open(_INSTALL_LOG, "w") as lf:
                for name, cmd in tools:
                    lf.write(f"Installing {name}...\n")
                    lf.flush()
                    try:
                        env = dict(__import__("os").environ, DEBIAN_FRONTEND="noninteractive")
                        result = subprocess.run(
                            cmd, capture_output=True, text=True, timeout=300, env=env,
                        )
                        if result.returncode == 0:
                            lf.write(f"  ✓ {name} installed\n")
                        else:
                            lf.write(f"  ✗ {name} failed: {result.stderr[:200]}\n")
                    except subprocess.TimeoutExpired:
                        lf.write(f"  ✗ {name} timed out (5min)\n")
                    except Exception as e:
                        lf.write(f"  ✗ {name} error: {e}\n")
                    lf.flush()

                # Stop freshclam service if it auto-started
                subprocess.run(
                    ["sudo", "systemctl", "stop", "clamav-freshclam"],
                    capture_output=True, timeout=10,
                )
                subprocess.run(
                    ["sudo", "systemctl", "disable", "clamav-freshclam"],
                    capture_output=True, timeout=10,
                )

                # Update virus DB in background
                subprocess.Popen(
                    ["sudo", "freshclam", "--quiet"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                lf.write("\nDone. Virus definitions updating in background.\n")
        finally:
            _INSTALL_LOCK.unlink(missing_ok=True)

    asyncio.create_task(_install())
    return {"ok": True, "message": "Installation started in background"}


# ── Security Fix (direct commands) ────────────────────────────────────────────

class SecurityFixRequest(BaseModel):
    command: str
    dry_run: bool = False


@router.post("/security/fix")
async def security_fix(payload: SecurityFixRequest):
    """Run a security fix command. Shell metacharacters are blocked."""
    import shlex

    # Block shell metacharacters — prevents injection via ;, &&, |, $(), etc.
    SHELL_METACHARS = set(';|&$`><(){}!')
    cmd = payload.command.strip()

    if any(ch in cmd for ch in SHELL_METACHARS):
        return {"ok": False, "output": "Command contains shell metacharacters — blocked for security"}

    ALLOWED_PREFIXES = [
        "find /tmp", "find /dev/shm",
        "grep ", "apt list", "apt-get",
        "systemctl", "clamscan", "sudo chkrootkit",
        "sudo apt-get", "which ", "echo ",
    ]
    if not any(cmd.startswith(pfx) for pfx in ALLOWED_PREFIXES):
        return {"ok": False, "output": f"Command not allowed: {cmd[:50]}"}

    try:
        args = shlex.split(cmd)
    except ValueError as e:
        return {"ok": False, "output": f"Invalid command syntax: {e}"}

    try:
        result = subprocess.run(
            args, capture_output=True, text=True, timeout=30,
        )
        output = (result.stdout.strip() + "\n" + result.stderr.strip()).strip()
        return {"ok": True, "output": output or "(no output)"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "output": "Command timed out (30s)"}
    except FileNotFoundError:
        return {"ok": False, "output": f"Command not found: {args[0]}"}
    except Exception as e:
        return {"ok": False, "output": f"Error: {e}"}
