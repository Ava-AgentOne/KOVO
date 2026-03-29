"""
Heartbeat scheduler — APScheduler periodic tasks.

Core jobs (always active):
  - auto_extract:                Daily 23:00 — extract learnings to MEMORY.md + SQLite
  - weekly_memory_consolidation: Sunday 03:30 — archive MEMORY.md if >500 lines
  - archive_logs:                Daily 03:00 — archive daily logs older than 30 days
  - version_check:               Daily 10:00 — check GitHub for new KOVO releases
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.memory.manager import MemoryManager
from src.tools.ollama import OllamaClient
from src.heartbeat.version_check import check_and_notify as _version_check

log = logging.getLogger(__name__)
logging.getLogger("apscheduler").setLevel(logging.WARNING)

_DUBAI_TZ = timezone(timedelta(hours=4))


def _dubai_today() -> date:
    return datetime.now(_DUBAI_TZ).date()


class HeartbeatScheduler:
    def __init__(
        self,
        reporter=None,
        ollama: OllamaClient | None = None,
        memory: MemoryManager | None = None,
        quick_interval_minutes: int = 30,
        full_interval_hours: int = 6,
        morning_time: str = "08:00",
        storage=None,
        auto_extractor=None,
    ):
        self.reporter = reporter
        self.ollama = ollama
        self.memory = memory
        self.storage = storage
        self.auto_extractor = auto_extractor
        self._scheduler = AsyncIOScheduler(timezone="Asia/Dubai")
        self._started = False

        # For version_check notifications
        self._tg_bot = None
        self._owner_user_id = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        if self._started:
            return

        # Archive old logs — daily at 03:00
        self._scheduler.add_job(
            self._archive_logs,
            trigger=CronTrigger(hour=3, minute=0, timezone="Asia/Dubai"),
            id="archive_logs",
            replace_existing=True,
        )

        # Auto-memory extraction — daily at 23:00
        if self.auto_extractor is not None:
            self._scheduler.add_job(
                self._auto_extract,
                trigger=CronTrigger(hour=23, minute=0, timezone="Asia/Dubai"),
                id="auto_extract",
                replace_existing=True,
            )
            # Weekly memory consolidation — Sunday 03:30
            self._scheduler.add_job(
                self._weekly_memory_consolidation,
                trigger=CronTrigger(
                    day_of_week="sun",
                    hour=3,
                    minute=30,
                    timezone="Asia/Dubai",
                ),
                id="weekly_memory_consolidation",
                replace_existing=True,
            )

        # Daily version check — 10:00
        self._scheduler.add_job(
            self._check_for_updates,
            trigger=CronTrigger(hour=10, minute=0, timezone="Asia/Dubai"),
            id="version_check",
            replace_existing=True,
        )

        self._scheduler.start()
        self._started = True
        job_count = len(self._scheduler.get_jobs())
        log.info("Heartbeat scheduler started: %d jobs", job_count)

    def stop(self) -> None:
        if self._started and self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            self._started = False
            log.info("Heartbeat scheduler stopped")

    # ------------------------------------------------------------------
    # Jobs
    # ------------------------------------------------------------------

    async def _archive_logs(self) -> None:
        """Archive daily logs older than 30 days."""
        try:
            n = self.memory.archive_old_logs(days=30)
            if n:
                log.info("Archived %d old daily logs", n)
        except Exception as e:
            log.error("Log archival failed: %s", e)

    async def _auto_extract(self) -> None:
        """Daily 23:00: extract learnings into MEMORY.md + SQLite."""
        if self.auto_extractor is None:
            return
        log.info("Running auto-memory extraction")
        try:
            result = await self.auto_extractor.extract_and_store()
            log.info("Auto-extract: %s", result)
        except Exception as e:
            log.error("Auto-extract failed: %s", e)

    async def _weekly_memory_consolidation(self) -> None:
        """Sunday 03:30: archive MEMORY.md if >500 lines."""
        if self.auto_extractor is None:
            return
        log.info("Running weekly memory budget check")
        try:
            self.auto_extractor._check_memory_budget()
        except Exception as e:
            log.error("Weekly memory consolidation failed: %s", e)

    async def _check_for_updates(self) -> None:
        """Check GitHub for KOVO updates and notify owner."""
        try:
            tg_bot = self._tg_bot
            owner_id = self._owner_user_id
            if tg_bot and owner_id:
                await _version_check(tg_bot, owner_id)
        except Exception as e:
            log.warning("Version check job failed: %s", e)

    # ------------------------------------------------------------------
    # Manual triggers (dashboard API / Telegram)
    # ------------------------------------------------------------------

    async def run_quick_check_now(self) -> str:
        """Trigger a quick check and return the result as text."""
        from src.heartbeat.checks import gather_quick_health, check_thresholds
        health = gather_quick_health()
        alerts = check_thresholds(health)
        if alerts:
            return "\n".join(alerts) + "\n\n```\n" + health[:800] + "\n```"
        return "✅ All clear\n\n```\n" + health[:800] + "\n```"

    async def run_full_report_now(self) -> str:
        """Trigger a full report and return the result as text."""
        from src.heartbeat.checks import gather_full_health, check_thresholds
        health = gather_full_health()
        alerts = check_thresholds(health)
        alert_prefix = ("\n".join(alerts) + "\n\n") if alerts else ""
        return alert_prefix + "```\n" + health[:2500] + "\n```"
