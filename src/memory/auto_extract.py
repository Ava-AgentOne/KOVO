"""
Auto-memory extraction with Pinned + Learnings system.

Daily at 23:00, reads today's log, calls Claude Sonnet to extract:
  - Pinned facts: key-value pairs that update in place
  - Learnings: rolling log entries, archived when MEMORY.md grows large
"""
from __future__ import annotations

import hashlib
import logging
import re
from datetime import date, datetime, timedelta, timezone
from difflib import SequenceMatcher
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.memory.manager import MemoryManager
    from src.memory.structured_store import StructuredStore

from src.utils.tz import get_tz as _get_configured_tz
log = logging.getLogger(__name__)

_INPUT_CAP = 3200
_MEMORY_BUDGET = 500

_EXTRACTION_PROMPT = """\
You are Kovo's memory extractor. Read the conversation log and extract \
the most important facts and learnings about the owner.

Output TWO sections:

### PINNED
Key facts about the owner that should be remembered permanently. \
If a fact changes, output the NEW value — it replaces the old one.

Format: - key: value
Use lowercase keys with underscores.
Examples:
- preferred_language: Arabic and English
- timezone: Asia/Dubai
- occupation: Software Engineer

Only output pinned entries for NEW or CHANGED owner info. \
Skip if nothing about the owner's profile/preferences was mentioned.

### LEARNINGS
Project notes, decisions, and facts worth remembering.

Format: - [category] fact here
Categories: preference, project, tool, person, decision, reminder

Rules:
- 0-5 pinned entries (only if new/changed)
- 3-8 learning bullets
- Be concise and specific
- Skip routine exchanges, metrics, transient info

Log:
{log_content}

Extract:"""


class AutoMemoryExtractor:

    def __init__(self, memory_manager: "MemoryManager", structured_store: "StructuredStore | None" = None):
        self.memory = memory_manager
        self.store = structured_store
        self._last_extract_date: date | None = None

    async def extract_and_store(self, force: bool = False) -> str:
        today = datetime.now(_get_configured_tz()).date()
        if not force and self._last_extract_date == today:
            return "Already extracted today."

        today_log = self.memory.daily_log()
        if not today_log or len(today_log.strip()) < 100:
            return "Not enough activity in today's log."

        log.info("Auto-memory extraction starting for %s", today)
        try:
            pinned, learnings = await self._call_extraction(today_log)
        except Exception as e:
            log.error("Extraction call failed: %s", e)
            return f"Extraction failed: {e}"

        pinned_count = 0
        for key, value in pinned:
            try:
                self.memory.update_pinned(key, value)
                pinned_count += 1
            except Exception as e:
                log.warning("Failed to update pinned '%s': %s", key, e)

        stored, dupes = 0, 0
        for bullet in learnings:
            if self._deduplicate(bullet):
                dupes += 1
                continue
            self._store_learning(bullet, date_str=today.isoformat())
            stored += 1

        self._last_extract_date = today
        self._check_memory_budget()

        status = f"Pinned: {pinned_count} updated. Learnings: {stored} new, {dupes} duplicates."
        log.info("Auto-extract: %s", status)
        return status

    async def _call_extraction(self, log_content: str) -> tuple[list[tuple[str, str]], list[str]]:
        import asyncio
        from src.tools.claude_cli import call_claude, extract_text

        capped = log_content[-_INPUT_CAP:]
        prompt = _EXTRACTION_PROMPT.format(log_content=capped)

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, lambda: call_claude(prompt, model="sonnet"),
        )
        text = extract_text(response)

        pinned: list[tuple[str, str]] = []
        learnings: list[str] = []
        section = None

        for line in text.splitlines():
            s = line.strip()
            if "PINNED" in s and s.startswith("#"):
                section = "pinned"
                continue
            elif "LEARNINGS" in s and s.startswith("#"):
                section = "learnings"
                continue
            if not s or s.startswith("#"):
                continue

            if section == "pinned" and s.startswith("- "):
                entry = s[2:].strip()
                ci = entry.find(":")
                if ci > 0:
                    k, v = entry[:ci].strip(), entry[ci+1:].strip()
                    if k and v:
                        pinned.append((k, v))

            elif section == "learnings" and s.startswith("- "):
                learnings.append(s[2:].strip())

        return pinned, learnings

    def _deduplicate(self, candidate: str) -> bool:
        cl = candidate.lower()
        if self.store:
            try:
                prefix = cl[:20].replace("%", "").replace("_", "")
                rows = self.store.execute(
                    "SELECT content FROM memories WHERE lower(content) LIKE ? LIMIT 20",
                    (f"%{prefix}%",),
                )
                for row in rows:
                    if SequenceMatcher(None, cl, row["content"].lower()).ratio() > 0.8:
                        return True
            except Exception:
                pass

        existing = self.memory.learnings_memory()
        for line in existing.splitlines():
            stripped = line.strip()
            if stripped and SequenceMatcher(None, cl, stripped.lower()).ratio() > 0.8:
                return True
        return False

    def _store_learning(self, content: str, source: str = "auto_extract", date_str: str | None = None) -> None:
        if not date_str:
            date_str = datetime.now(_get_configured_tz()).date().isoformat()
        category = "general"
        m = re.match(r"^\[(\w+)\]\s*(.*)", content)
        if m:
            category = m.group(1)
        if self.store:
            h = hashlib.sha256(content.lower().encode()).hexdigest()[:32]
            self.store.insert("memories", {
                "content": content,
                "category": category,
                "source": source,
                "created_at": f"{date_str} 00:00:00",
                "hash": h,
            })
        self.memory.flush_to_memory(content)

    def _check_memory_budget(self) -> None:
        """Archive Learnings if >500 lines. NEVER touches Pinned."""
        mem_path = self.memory.workspace / "MEMORY.md"
        if not mem_path.exists():
            return
        try:
            content = mem_path.read_text(encoding="utf-8")
            lines = content.splitlines()

            learnings_start = 0
            for i, line in enumerate(lines):
                if line.strip() == "## Learnings":
                    learnings_start = i
                    break

            learnings_lines = lines[learnings_start:]
            if len(learnings_lines) <= _MEMORY_BUDGET:
                return

            archive_dir = self.memory.workspace / "memory" / "archive"
            archive_dir.mkdir(parents=True, exist_ok=True)
            archive_path = archive_dir / "memories_archived.md"

            keep_from = len(lines) - 200
            if keep_from <= learnings_start:
                return

            to_archive = lines[learnings_start + 1:keep_from]
            to_keep = lines[:learnings_start + 1] + lines[keep_from:]

            with open(archive_path, "a", encoding="utf-8") as f:
                f.write("\n".join(to_archive) + "\n")

            mem_path.write_text("\n".join(to_keep), encoding="utf-8")
            log.info("Archived %d learnings, kept Pinned + %d recent",
                     len(to_archive), len(lines[keep_from:]))
        except Exception as e:
            log.error("Memory budget check failed: %s", e)
