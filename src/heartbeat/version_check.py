"""
Version check — periodically checks GitHub for new KOVO releases.
Sends a Telegram notification when an update is available.
"""
import json
import logging
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)

_UPDATE_SCRIPT = Path("/opt/kovo/scripts/update.sh")
_NOTIFIED_FILE = Path("/opt/kovo/data/.update_notified")


async def check_and_notify(tg_bot, owner_user_id: int) -> dict | None:
    """
    Check for updates and notify the owner via Telegram if one is available.
    Returns the update info dict, or None if no update / already notified.
    """
    if not _UPDATE_SCRIPT.exists():
        return None

    try:
        result = subprocess.run(
            ["bash", str(_UPDATE_SCRIPT), "--json"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return None

        info = json.loads(result.stdout.strip())
        if not info.get("update_available"):
            # Clear notification flag when user is up to date
            _NOTIFIED_FILE.unlink(missing_ok=True)
            return None

        remote_ver = info.get("remote_version", "?")

        # Don't notify twice for the same version
        if _NOTIFIED_FILE.exists():
            notified_ver = _NOTIFIED_FILE.read_text().strip()
            if notified_ver == remote_ver:
                return info  # Still available, but already notified

        # Send notification
        commit = info.get("latest_commit", {})
        commit_msg = commit.get("message", "")
        commit_date = commit.get("date", "")[:10]
        local_ver = info.get("local_version", "?")

        message = (
            f"🔄 *KOVO Update Available*\n\n"
            f"Current: v{local_ver}\n"
            f"Latest: v{remote_ver}\n"
        )
        if commit_msg:
            message += f"\n📝 _{commit_msg}_"
        if commit_date:
            message += f"\n📅 {commit_date}"
        message += (
            f"\n\nUpdate from the dashboard (Settings → Updates) "
            f"or run:\n`bash /opt/kovo/scripts/update.sh --apply`"
        )

        try:
            await tg_bot.send_message(
                chat_id=owner_user_id,
                text=message,
                parse_mode="Markdown",
            )
            log.info("Update notification sent: v%s → v%s", local_ver, remote_ver)
        except Exception as e:
            log.warning("Failed to send update notification: %s", e)

        # Mark as notified for this version
        _NOTIFIED_FILE.write_text(remote_ver)
        return info

    except Exception as e:
        log.warning("Version check failed: %s", e)
        return None
