"""
StorageManager — disk usage monitoring, automated garbage collection, and
user-approval cleanup for the Kovo data directory.

Directory tiers:
  Tier 1 (auto-purge, no approval): tmp (1d), audio (7d), screenshots (7d)
  Tier 2 (ask user): photos (30d), documents (30d), images (30d)
  Managed separately: backups (keep 30d), logs (logrotate handles rotation)
"""
from __future__ import annotations

import json
import logging
import os
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from src.utils.tz import get_tz as _get_tz
from src.utils.platform import data_path, kovo_dir, logs_path
from typing import Optional

log = logging.getLogger(__name__)

_BASE = data_path()
_SRC  = kovo_dir() / "src"
_LOGS = logs_path()

# name → (path, retention_days, tier)  tier=None means "keep, no auto-purge"
_DIR_CONFIG: dict[str, tuple[Path, int, Optional[int]]] = {
    "tmp":         (_BASE / "tmp",         1,  1),
    "audio":       (_BASE / "audio",       7,  1),
    "screenshots": (_BASE / "screenshots", 7,  1),
    "photos":      (_BASE / "photos",      30, 2),
    "documents":   (_BASE / "documents",   30, 2),
    "images":      (_BASE / "images",      30, 2),
    "backups":     (_BASE / "backups",     30, None),
}

_WARN_THRESHOLD    = 0.15         # alert when free < 15 %
_NOTIFY_MIN_FREED  = 10 << 20    # only notify auto_purge if freed ≥ 10 MB


# ── Helpers ────────────────────────────────────────────────────────────────────

def _dir_size(path: Path) -> int:
    """Recursively sum file sizes under path (bytes). Never raises."""
    total = 0
    try:
        for entry in os.scandir(path):
            try:
                if entry.is_file(follow_symlinks=False):
                    total += entry.stat().st_size
                elif entry.is_dir(follow_symlinks=False):
                    total += _dir_size(Path(entry.path))
            except OSError:
                pass
    except OSError:
        pass
    return total


def _fmt(size_bytes: int) -> str:
    """Human-readable size string."""
    if size_bytes >= 1_073_741_824:
        return f"{size_bytes / 1_073_741_824:.1f}GB"
    if size_bytes >= 1_048_576:
        return f"{size_bytes / 1_048_576:.0f}MB"
    if size_bytes >= 1024:
        return f"{size_bytes / 1024:.0f}KB"
    return f"{size_bytes}B"


# ── StorageManager ─────────────────────────────────────────────────────────────

class StorageManager:
    """Manages data directory lifecycle, disk monitoring, and GC."""

    def __init__(self, base_dir: Path = _BASE) -> None:
        self._base = base_dir
        self._state_file = base_dir / ".storage_state.json"
        self._ensure_dirs()

    # ── Lifecycle ──────────────────────────────────────────────────────────

    def _ensure_dirs(self) -> None:
        for _, (path, _, _) in _DIR_CONFIG.items():
            path.mkdir(parents=True, exist_ok=True)

    def _load_state(self) -> dict:
        try:
            if self._state_file.exists():
                return json.loads(self._state_file.read_text())
        except Exception:
            pass
        return {}

    def _save_state(self, state: dict) -> None:
        try:
            self._state_file.write_text(json.dumps(state, indent=2))
        except Exception as e:
            log.warning("Could not save storage state: %s", e)

    # ── Core API ───────────────────────────────────────────────────────────

    def get_disk_usage(self) -> dict:
        """
        Returns:
          total_gb, used_gb, free_gb, free_percent  — whole-disk stats
          dir_sizes: dict[name, bytes]               — per data subdirectory
          warning: bool                              — True if free < 15 %
        """
        du = shutil.disk_usage("/")
        free_pct = du.free / du.total

        dir_sizes: dict[str, int] = {}
        for name, (path, _, _) in _DIR_CONFIG.items():
            dir_sizes[name] = _dir_size(path)
        dir_sizes["logs"] = _dir_size(_LOGS)

        return {
            "total_gb":    du.total / 1e9,
            "used_gb":     du.used  / 1e9,
            "free_gb":     du.free  / 1e9,
            "free_percent": free_pct,
            "dir_sizes":   dir_sizes,
            "warning":     free_pct < _WARN_THRESHOLD,
        }

    def auto_purge(self) -> dict:
        """
        Tier 1: delete files past their retention without user approval.
        Covers: tmp (1d), audio (7d), screenshots (7d).

        Returns: {deleted: int, freed_bytes: int, details: list[str]}
        """
        now = datetime.now(tz=_get_tz())
        deleted = 0
        freed_bytes = 0
        details: list[str] = []

        for name, (path, retention_days, tier) in _DIR_CONFIG.items():
            if tier != 1:
                continue
            cutoff = now - timedelta(days=retention_days)
            n, freed = self._purge_dir_older_than(path, cutoff)
            if n:
                details.append(f"{name}/: {n} files freed {_fmt(freed)}")
                deleted += n
                freed_bytes += freed


        state = self._load_state()
        state["last_auto_purge"] = now.isoformat()
        self._save_state(state)

        log.info("auto_purge: deleted=%d freed=%s", deleted, _fmt(freed_bytes))
        return {"deleted": deleted, "freed_bytes": freed_bytes, "details": details}

    def scan_purgeable(self) -> dict:
        """
        Tier 2: find old files that need user approval before deletion.
        Covers: photos (30d), documents (30d), images (30d).

        Returns:
          dict[dir_name, {files: list[str], count: int, total_size: int, total_mb: float}]
        """
        now = datetime.now(tz=_get_tz())
        result: dict[str, dict] = {}

        for name, (path, retention_days, tier) in _DIR_CONFIG.items():
            if tier != 2:
                continue
            cutoff = now - timedelta(days=retention_days)
            files: list[str] = []
            total_size = 0
            try:
                for f in path.iterdir():
                    if not f.is_file():
                        continue
                    try:
                        mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=_get_tz())
                        if mtime < cutoff:
                            size = f.stat().st_size
                            files.append(str(f))
                            total_size += size
                    except OSError:
                        pass
            except OSError:
                pass

            if files:
                result[name] = {
                    "files":      files,
                    "count":      len(files),
                    "total_size": total_size,
                    "total_mb":   round(total_size / 1_048_576, 1),
                }

        return result

    def purge_files(self, file_paths: list[str]) -> dict:
        """
        Delete a specific list of approved files.
        Returns: {deleted: int, freed_mb: float}
        """
        deleted = 0
        freed_bytes = 0
        for path_str in file_paths:
            p = Path(path_str)
            try:
                size = p.stat().st_size
                p.unlink()
                deleted += 1
                freed_bytes += size
            except Exception as e:
                log.warning("Could not delete %s: %s", path_str, e)
        log.info("purge_files: deleted=%d freed=%.1fMB", deleted, freed_bytes / 1_048_576)
        return {"deleted": deleted, "freed_mb": round(freed_bytes / 1_048_576, 1)}

    def format_storage_report(self) -> str:
        """Formatted text for the /storage Telegram command."""
        usage = self.get_disk_usage()
        total_gb  = usage["total_gb"]
        used_gb   = usage["used_gb"]
        free_gb   = usage["free_gb"]
        free_pct  = usage["free_percent"] * 100
        dir_sizes = usage["dir_sizes"]

        state = self._load_state()
        last_purge = "never"
        if "last_auto_purge" in state:
            try:
                last_dt = datetime.fromisoformat(state["last_auto_purge"])
                delta   = datetime.now(tz=_get_tz()) - last_dt
                hours   = int(delta.total_seconds() / 3600)
                last_purge = f"{hours}h ago" if hours else "just now"
            except Exception:
                pass

        warn_line = "⚠️ *Low disk space!*\n\n" if usage["warning"] else ""

        rows = [
            ("audio",        "auto-purge: 7 days"),
            ("photos",       "review: 30 days"),
            ("documents",    "review: 30 days"),
            ("images",       "review: 30 days"),
            ("screenshots",  "auto-purge: 7 days"),
            ("tmp",          "auto-purge: 1 day"),
            ("backups",      "keep: 30 days"),
            ("logs",         "logrotate: 7 days"),
        ]
        table = ""
        for dir_name, policy in rows:
            size_str = _fmt(dir_sizes.get(dir_name, 0)).rjust(7)
            table += f"`📁 {dir_name:<13}{size_str}  ({policy})`\n"

        return (
            f"📊 *Storage Report*\n\n"
            f"Disk: {used_gb:.1f}GB / {total_gb:.0f}GB "
            f"({100 - free_pct:.0f}% used, {free_gb:.1f}GB free)\n\n"
            f"{warn_line}"
            f"{table}\n"
            f"Last auto-purge: {last_purge}"
        )

    def build_low_disk_alert(self, usage: Optional[dict] = None) -> str:
        """Build the ⚠️ Low Disk Space alert message."""
        if usage is None:
            usage = self.get_disk_usage()
        free_gb   = usage["free_gb"]
        free_pct  = usage["free_percent"] * 100
        dir_sizes = usage["dir_sizes"]

        top = sorted(dir_sizes.items(), key=lambda x: x[1], reverse=True)[:3]
        top_lines = "".join(
            f"  📁 {name}/  {_fmt(size)}\n"
            for name, size in top
            if size > 0
        )
        auto_freeable = dir_sizes.get("audio", 0) + dir_sizes.get("screenshots", 0)

        return (
            f"⚠️ *Low Disk Space!*\n\n"
            f"Only {free_gb:.1f}GB free ({free_pct:.1f}%)\n\n"
            f"Top space users:\n{top_lines}\n"
            f"I can auto-purge audio and screenshots to free ~{_fmt(auto_freeable)}.\n"
            f"Run /purge all to also clean old photos/documents.\n"
            f"Or run /storage for the full report."
        )

    # ── Internal helpers ───────────────────────────────────────────────────

    def _purge_dir_older_than(self, path: Path, cutoff: datetime) -> tuple[int, int]:
        """Delete files in path with mtime before cutoff. Returns (count, bytes)."""
        deleted = 0
        freed = 0
        try:
            for f in path.iterdir():
                if not f.is_file():
                    continue
                try:
                    mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=_get_tz())
                    if mtime < cutoff:
                        size = f.stat().st_size
                        f.unlink()
                        deleted += 1
                        freed += size
                except Exception as e:
                    log.warning("Could not delete %s: %s", f, e)
        except OSError as e:
            log.warning("Could not scan %s: %s", path, e)
        return deleted, freed
