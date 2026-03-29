"""
Workspace memory manager — reads/writes OpenClaw-compatible Markdown files.

MEMORY.md has two sections:
  ## Pinned — key-value facts that update in place (always loaded by brain)
  ## Learnings — rolling log entries (loaded on demand, archived when large)
"""
import logging
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from src.utils.tz import get_tz, today as _tz_today


def _dubai_today() -> date:
    return _tz_today()

log = logging.getLogger(__name__)


class MemoryManager:
    def __init__(self, workspace_dir: Path):
        self.workspace = workspace_dir

    def _read(self, path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return ""

    # ── Workspace file readers ────────────────────────────────────────────

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

    # ── Pinned + Learnings section readers ─────────────────────────────────

    def pinned_memory(self) -> str:
        """Return the Pinned section of MEMORY.md."""
        mem = self.main_memory()
        return self._extract_section(mem, "Pinned")

    def learnings_memory(self) -> str:
        """Return the Learnings section of MEMORY.md."""
        mem = self.main_memory()
        return self._extract_section(mem, "Learnings")

    def _extract_section(self, text: str, section_name: str) -> str:
        """Extract content between ## section_name and the next ## heading."""
        pattern = rf"^## {re.escape(section_name)}\s*\n(.*?)(?=^## |\Z)"
        match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
        if match:
            content = re.sub(r"<!--.*?-->", "", match.group(1)).strip()
            return content
        return ""

    # ── Pinned entry management ───────────────────────────────────────────

    def update_pinned(self, key: str, value: str) -> None:
        """
        Update a pinned entry in MEMORY.md.
        If the key exists, replace the value in place.
        If the key doesn't exist, add it to the Pinned section.
        """
        mem_path = self.workspace / "MEMORY.md"
        if not mem_path.exists():
            mem_path.write_text(
                f"# MEMORY.md\n\n## Pinned\n- {key}: {value}\n\n## Learnings\n"
            )
            log.info("Created MEMORY.md with pinned: %s", key)
            return

        content = mem_path.read_text(encoding="utf-8")
        key_lower = key.lower().strip()
        new_line = f"- {key}: {value}"
        lines = content.split("\n")

        in_pinned = False
        found = False
        result = []

        for line in lines:
            stripped = line.strip()

            if stripped == "## Pinned":
                in_pinned = True
                result.append(line)
                continue

            if stripped.startswith("## ") and stripped != "## Pinned":
                if in_pinned and not found:
                    result.append(new_line)
                    found = True
                in_pinned = False
                result.append(line)
                continue

            if in_pinned and stripped.startswith("- "):
                entry = stripped[2:]
                colon_idx = entry.find(":")
                if colon_idx > 0:
                    existing_key = entry[:colon_idx].strip().lower()
                    if existing_key == key_lower:
                        result.append(new_line)
                        found = True
                        continue

            result.append(line)

        if not found:
            final = []
            added = False
            for line in result:
                final.append(line)
                if line.strip() == "## Pinned" and not added:
                    final.append(new_line)
                    added = True
            result = final

        mem_path.write_text("\n".join(result), encoding="utf-8")
        log.info("Pinned memory %s: %s = %s", "updated" if found else "added", key, value)

    def remove_pinned(self, key: str) -> bool:
        """Remove a pinned entry by key. Returns True if found and removed."""
        mem_path = self.workspace / "MEMORY.md"
        if not mem_path.exists():
            return False

        content = mem_path.read_text(encoding="utf-8")
        key_lower = key.lower().strip()
        lines = content.split("\n")
        result = []
        removed = False
        in_pinned = False

        for line in lines:
            stripped = line.strip()
            if stripped == "## Pinned":
                in_pinned = True
            elif stripped.startswith("## "):
                in_pinned = False

            if in_pinned and stripped.startswith("- "):
                entry = stripped[2:]
                colon_idx = entry.find(":")
                if colon_idx > 0:
                    existing_key = entry[:colon_idx].strip().lower()
                    if existing_key == key_lower:
                        removed = True
                        continue
            result.append(line)

        if removed:
            mem_path.write_text("\n".join(result), encoding="utf-8")
            log.info("Pinned memory removed: %s", key)
        return removed

    # ── System prompt builder ─────────────────────────────────────────────

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
            today_log = self.daily_log()
            if today_log:
                parts.append("---\n## Today's Activity\n" + today_log)
            yesterday_log = self.daily_log(_dubai_today() - timedelta(days=1))
            if yesterday_log:
                parts.append("---\n## Yesterday's Activity\n" + yesterday_log)
            pinned = self.pinned_memory()
            if pinned:
                parts.append("---\n## Key Facts\n" + pinned)
            learnings = self.learnings_memory()
            if learnings:
                parts.append("---\n## Learnings\n" + learnings[-2000:])
        return "\n\n".join(parts)

    # ── Write operations ──────────────────────────────────────────────────

    def flush_to_memory(self, learnings: str) -> None:
        """Append a learning entry to the ## Learnings section of MEMORY.md."""
        mem_path = self.workspace / "MEMORY.md"
        today = _dubai_today().isoformat()
        entry = f"- {today}: {learnings.strip()}"

        if not mem_path.exists():
            mem_path.write_text(
                f"# MEMORY.md\n\n## Pinned\n\n## Learnings\n{entry}\n"
            )
            log.info("Created MEMORY.md with first learning")
            return

        content = mem_path.read_text(encoding="utf-8")
        if "## Learnings" in content:
            content = content.rstrip() + f"\n{entry}\n"
        else:
            content += f"\n\n## Learnings\n{entry}\n"

        mem_path.write_text(content, encoding="utf-8")
        log.info("Flushed learning to MEMORY.md")

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

    def archive_old_logs(self, days: int = 30) -> int:
        """Move daily log files older than `days` to memory/archive/."""
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
