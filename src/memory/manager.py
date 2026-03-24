"""
Workspace memory manager — reads/writes OpenClaw-compatible Markdown files.
"""
import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

# All timestamps use Dubai local time (UTC+4)
_DUBAI_TZ = timezone(timedelta(hours=4))


def _dubai_today() -> date:
    return datetime.now(_DUBAI_TZ).date()

log = logging.getLogger(__name__)


class MemoryManager:
    def __init__(self, workspace_dir: Path):
        self.workspace = workspace_dir

    def _read(self, path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return ""

    def soul(self) -> str:
        return self._read(self.workspace / "SOUL.md")

    def user_profile(self) -> str:
        return self._read(self.workspace / "USER.md")

    def identity(self) -> str:
        return self._read(self.workspace / "IDENTITY.md")

    def heartbeat(self) -> str:
        return self._read(self.workspace / "HEARTBEAT.md")

    def main_memory(self) -> str:
        return self._read(self.workspace / "MEMORY.md")

    def daily_log(self, for_date: date | None = None) -> str:
        d = for_date or _dubai_today()
        path = self.workspace / "memory" / f"{d.isoformat()}.md"
        return self._read(path)

    def build_system_prompt(self, include_memory: bool = True) -> str:
        """Assemble a system prompt from workspace files."""
        parts = []
        soul = self.soul()
        if soul:
            parts.append(soul)
        user = self.user_profile()
        if user:
            parts.append("---\n" + user)
        if include_memory:
            # Today + yesterday
            today_log = self.daily_log()
            if today_log:
                parts.append("---\n## Today's Activity\n" + today_log)
            yesterday_log = self.daily_log(_dubai_today() - timedelta(days=1))
            if yesterday_log:
                parts.append("---\n## Yesterday's Activity\n" + yesterday_log)
            mem = self.main_memory()
            if mem:
                parts.append("---\n" + mem)
        return "\n\n".join(parts)

    def append_daily_log(self, entry: str, session_label: str | None = None) -> None:
        """Append an entry to today's daily log."""
        today = _dubai_today()
        log_dir = self.workspace / "memory"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"{today.isoformat()}.md"

        header = f"# {today.isoformat()}\n\n" if not log_path.exists() else ""
        label = session_label or "Session"

        with open(log_path, "a", encoding="utf-8") as f:
            if header:
                f.write(header)
            f.write(f"## {label}\n{entry}\n\n")

        log.debug("Appended to daily log: %s", log_path)

    def flush_to_memory(self, learnings: str) -> None:
        """
        Append important learnings to MEMORY.md (end-of-day flush).
        Prepends a date header so entries are searchable.
        """
        mem_path = self.workspace / "MEMORY.md"
        today = _dubai_today().isoformat()
        entry = f"\n\n## {today}\n{learnings.strip()}\n"
        with open(mem_path, "a", encoding="utf-8") as f:
            f.write(entry)
        log.info("Flushed learnings to MEMORY.md")

    def archive_old_logs(self, days: int = 30) -> int:
        """
        Move daily log files older than `days` to memory/archive/.
        Returns number of files archived.
        """
        log_dir = self.workspace / "memory"
        archive_dir = log_dir / "archive"
        archive_dir.mkdir(parents=True, exist_ok=True)
        cutoff = _dubai_today() - timedelta(days=days)
        archived = 0
        for log_file in log_dir.glob("????-??-??.md"):
            try:
                file_date = date.fromisoformat(log_file.stem)
                if file_date < cutoff:
                    log_file.rename(archive_dir / log_file.name)
                    archived += 1
            except ValueError:
                pass
        if archived:
            log.info("Archived %d old log files", archived)
        return archived
