"""
Off-site backups (v3.0 Phase 0) — nightly upload to Google Drive.

Backups previously lived ONLY in data/backups on the same VM they protect;
a dead disk would take KOVO and every backup of it together. This module
creates a fresh core backup, uploads it to a "KOVO Backups" folder in the
owner's Drive, and prunes old uploads to a retention count.

settings.yaml:
  backup:
    offsite:
      enabled: true      # default true when Google is configured
      keep: 7            # uploads retained in Drive

Run manually:  venv/bin/python -m src.tools.offsite_backup
Scheduled:     heartbeat scheduler, daily 04:00 (job id: offsite_backup)
"""
from __future__ import annotations

import logging
import subprocess

from src.utils.platform import data_path, kovo_dir

log = logging.getLogger(__name__)

FOLDER_NAME = "KOVO Backups"
FOLDER_MIME = "application/vnd.google-apps.folder"


def is_enabled() -> bool:
    """Enabled in config AND Google auth is set up."""
    from src.gateway import config as cfg
    conf = (cfg.get().get("backup") or {}).get("offsite") or {}
    if conf.get("enabled", True) is False:
        return False
    token = kovo_dir() / "config" / "google-token.json"
    return token.exists()


def _keep_count() -> int:
    from src.gateway import config as cfg
    conf = (cfg.get().get("backup") or {}).get("offsite") or {}
    try:
        return max(1, int(conf.get("keep", 7)))
    except (TypeError, ValueError):
        return 7


def _ensure_folder(api) -> str:
    """Find or create the Drive backup folder, return its id."""
    service = api._build("drive", "v3")
    res = service.files().list(
        q=f"name='{FOLDER_NAME}' and mimeType='{FOLDER_MIME}' and trashed=false",
        fields="files(id)",
        pageSize=1,
    ).execute()
    files = res.get("files", [])
    if files:
        return files[0]["id"]
    folder = service.files().create(
        body={"name": FOLDER_NAME, "mimeType": FOLDER_MIME},
        fields="id",
    ).execute()
    log.info("Created Drive folder '%s'", FOLDER_NAME)
    return folder["id"]


def select_prunable(files: list[dict], keep: int) -> list[dict]:
    """Files to delete: everything beyond the newest `keep` by createdTime.
    Pure function — unit tested."""
    ordered = sorted(files, key=lambda f: f.get("createdTime", ""), reverse=True)
    return ordered[keep:]


def _prune(api, folder_id: str, keep: int) -> int:
    service = api._build("drive", "v3")
    res = service.files().list(
        q=f"'{folder_id}' in parents and trashed=false",
        fields="files(id,name,createdTime)",
        pageSize=100,
    ).execute()
    doomed = select_prunable(res.get("files", []), keep)
    for f in doomed:
        try:
            service.files().delete(fileId=f["id"]).execute()
            log.info("Pruned old off-site backup: %s", f["name"])
        except Exception as e:
            log.warning("Prune failed for %s: %s", f.get("name"), e)
    return len(doomed)


def run_offsite_backup() -> dict:
    """Create a fresh core backup, upload to Drive, prune. Sync — call via
    asyncio.to_thread from async contexts. Returns {ok, ...} always."""
    try:
        script = kovo_dir() / "scripts" / "backup.sh"
        result = subprocess.run(
            ["bash", str(script)], capture_output=True, text=True, timeout=300,
        )
        if result.returncode != 0:
            return {"ok": False, "error": f"backup.sh failed: {result.stderr.strip()[-300:]}"}

        backups = sorted(
            (data_path() / "backups").glob("kovo-backup-*.tar.gz"),
            key=lambda f: f.stat().st_mtime,
        )
        if not backups:
            return {"ok": False, "error": "no backup archive found after backup.sh"}
        newest = backups[-1]

        from src.tools.google_api import GoogleAPI
        api = GoogleAPI()
        folder_id = _ensure_folder(api)
        uploaded = api.upload_file(str(newest), parent_folder_id=folder_id)
        pruned = _prune(api, folder_id, _keep_count())

        size_mb = round(newest.stat().st_size / 1e6, 1)
        log.info("Off-site backup uploaded: %s (%.1f MB), pruned %d old",
                 newest.name, size_mb, pruned)
        return {"ok": True, "name": newest.name, "size_mb": size_mb,
                "pruned": pruned, "link": uploaded.get("webViewLink")}
    except Exception as e:
        log.error("Off-site backup failed: %s", e)
        return {"ok": False, "error": str(e)[:300]}


if __name__ == "__main__":
    import json
    print(json.dumps(run_offsite_backup(), indent=2))
