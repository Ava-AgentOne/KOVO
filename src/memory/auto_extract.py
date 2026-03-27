"""
Auto-memory extraction.
Once per day (triggered by scheduler at 23:00), reads today's conversation log,
calls Claude Sonnet to extract key facts/learnings, deduplicates via SQL + difflib,
and stores results to MEMORY.md + SQLite memories table.
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

_DUBAI_TZ = timezone(timedelta(hours=4))

log = logging.getLogger(__name__)

# Capped at ~3200 chars ≈ 4000 tokens input budget
_INPUT_CAP = 3200
# Max lines in MEMORY.md before archival kicks in
_MEMORY_BUDGET = 500

_EXTRACTION_PROMPT = """\
You are Kovo's memory extractor. Read the conversation log below and extract \
the most important facts, preferences, and learnings about the owner and his projects.

Rules:
- Extract 3-8 bullet points maximum
- Each bullet: concise, specific, factual (not vague like "the owner likes good code")
- Focus on: preferences, decisions, project facts, recurring topics, things to remember
- Skip: routine exchanges, errors already fixed, system metrics, transient info
- Do NOT extract timestamps, permission grants, or trivial chat

Format each bullet exactly like:
- [category] fact or learning here

Categories: preference, project, tool, person, decision, reminder

Log:
{log_content}

Extract:"""


class AutoMemoryExtractor:
    """Extracts key learnings from daily logs and stores them deduped in MEMORY.md + SQLite."""

    def __init__(self, memory_manager: "MemoryManager", structured_store: "StructuredStore | None" = None):
        self.memory = memory_manager
        self.store = structured_store
        self._last_extract_date: date | None = None

    # ── Public API ────────────────────────────────────────────────────────

    async def extract_and_store(self, force: bool = False) -> str:
        """
        Extract learnings from today's log and store them.
        Skips if already run today unless force=True.
        Returns a human-readable status string.
        """
        today = datetime.now(_DUBAI_TZ).date()
        if not force and self._last_extract_date == today:
            return "Already extracted today."

        today_log = self.memory.daily_log()
        if not today_log or len(today_log.strip()) < 100:
            return "Not enough activity in today's log."

        log.info("Auto-memory extraction starting for %s", today)
        try:
            bullets = await self._call_extraction(today_log)
        except Exception as e:
            log.error("Extraction call failed: %s", e)
            return f"Extraction failed: {e}"

        if not bullets:
            return "No learnings extracted."

        stored, dupes = 0, 0
        for bullet in bullets:
            if self._deduplicate(bullet):
                dupes += 1
                continue
            self._store_memory(bullet, source="auto_extract", date_str=today.isoformat())
            stored += 1

        self._last_extract_date = today
        self._check_memory_budget()

        log.info("Auto-extract complete: %d stored, %d duplicates", stored, dupes)
        return f"Extracted {stored} new memories ({dupes} duplicates skipped)."

    # ── Internal ──────────────────────────────────────────────────────────

    async def _call_extraction(self, log_content: str) -> list[str]:
        """Call Claude Sonnet to extract learnings. Input capped at _INPUT_CAP chars."""
        import asyncio
        from src.tools.claude_cli import call_claude, extract_text

        capped = log_content[-_INPUT_CAP:]
        prompt = _EXTRACTION_PROMPT.format(log_content=capped)

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: call_claude(prompt, model="sonnet"),
        )
        text = extract_text(response)

        bullets = []
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("- "):
                bullets.append(line[2:].strip())
        return bullets

    def _deduplicate(self, candidate: str) -> bool:
        """
        Returns True if candidate is a near-duplicate of an existing memory.
        Uses SQL LIKE for coarse match, then difflib ratio > 0.8 for confirmation.
        No LLM call.
        """
        candidate_lower = candidate.lower()

        # SQL coarse check against stored memories
        if self.store:
            try:
                # Use first 20 chars as a coarse search key
                prefix = candidate_lower[:20].replace("%", "").replace("_", "")
                rows = self.store.execute(
                    "SELECT content FROM memories WHERE lower(content) LIKE ? LIMIT 20",
                    (f"%{prefix}%",),
                )
                for row in rows:
                    ratio = SequenceMatcher(None, candidate_lower, row["content"].lower()).ratio()
                    if ratio > 0.8:
                        return True
            except Exception as e:
                log.debug("Dedup SQL check failed: %s", e)

        # Fallback: scan MEMORY.md lines with difflib
        existing = self.memory.main_memory()
        for line in existing.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            ratio = SequenceMatcher(None, candidate_lower, stripped.lower()).ratio()
            if ratio > 0.8:
                return True

        return False

    def _store_memory(self, content: str, source: str = "auto_extract", date_str: str | None = None) -> None:
        """Store a memory bullet in both MEMORY.md and SQLite."""
        if not date_str:
            date_str = datetime.now(_DUBAI_TZ).date().isoformat()

        # Parse "[category] content" format
        category = "general"
        cat_match = re.match(r"^\[(\w+)\]\s*(.*)", content)
        if cat_match:
            category = cat_match.group(1)

        # Store in SQLite
        if self.store:
            content_hash = hashlib.sha256(content.lower().encode()).hexdigest()[:32]
            self.store.insert("memories", {
                "content": content,
                "category": category,
                "source": source,
                "created_at": f"{date_str} 00:00:00",
                "hash": content_hash,
            })

        # Append to MEMORY.md (one bullet per call)
        self.memory.flush_to_memory(f"- {content}")

    def _check_memory_budget(self) -> None:
        """Archive MEMORY.md if it exceeds _MEMORY_BUDGET lines."""
        mem_path = self.memory.workspace / "MEMORY.md"
        if not mem_path.exists():
            return
        try:
            lines = mem_path.read_text(encoding="utf-8").splitlines()
            if len(lines) <= _MEMORY_BUDGET:
                return

            archive_dir = self.memory.workspace / "memory" / "archive"
            archive_dir.mkdir(parents=True, exist_ok=True)
            archive_path = archive_dir / "memories_archived.md"

            split_at = len(lines) - 200
            to_archive = lines[:split_at]
            to_keep = lines[split_at:]

            with open(archive_path, "a", encoding="utf-8") as f:
                f.write("\n".join(to_archive) + "\n")
            mem_path.write_text("\n".join(to_keep), encoding="utf-8")
            log.info("Memory archived %d lines, kept %d", split_at, len(to_keep))
        except Exception as e:
            log.error("Memory budget check failed: %s", e)
