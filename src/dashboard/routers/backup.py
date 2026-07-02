"""
Backup and restore endpoints.
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

        # Validate archive contents BEFORE any extraction
        import tarfile as _tf_check
        try:
            with _tf_check.open(tmp_path, "r:gz") as check_tar:
                for member in check_tar.getmembers():
                    if member.name.startswith("/") or ".." in member.name:
                        return {"ok": False, "output": f"Rejected: archive contains unsafe path '{member.name}'"}
                    if member.name.endswith(".py") and member.name.startswith("src/"):
                        return {"ok": False, "output": f"Rejected: archive contains source code '{member.name}' — use git pull for code updates"}
        except Exception as e:
            return {"ok": False, "output": f"Invalid archive: {e}"}

        # Extract using restore.sh (preferred) or raw tar
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
