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
from src.utils.tz import today as _tz_today

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from src.memory.manager import MemoryManager
from src.tools.ollama import OllamaClient
from src.heartbeat.version_check import check_and_notify as _version_check

log = logging.getLogger(__name__)
logging.getLogger("apscheduler").setLevel(logging.WARNING)

# Timezone from settings.yaml


def _dubai_today() -> date:
    return _tz_today()


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
        self._tz_name = self._get_tz_name()
        self._scheduler = AsyncIOScheduler(timezone=self._tz_name)
        self._started = False

        # For version_check notifications
        self._tg_bot = None
        self._owner_user_id = None

        # For reminder delivery
        self._reminders = None
        self._agent = None

    @staticmethod
    def _get_tz_name() -> str:
        try:
            from src.gateway.config import kovo_timezone
            return kovo_timezone()
        except Exception:
            return "UTC"

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        if self._started:
            return

        # Archive old logs — daily at 03:00
        self._scheduler.add_job(
            self._archive_logs,
            trigger=CronTrigger(hour=3, minute=0, timezone=self._tz_name),
            id="archive_logs",
            replace_existing=True,
        )

        # Auto-memory extraction — daily at 23:00
        if self.auto_extractor is not None:
            self._scheduler.add_job(
                self._auto_extract,
                trigger=CronTrigger(hour=23, minute=0, timezone=self._tz_name),
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
                    timezone=self._tz_name,
                ),
                id="weekly_memory_consolidation",
                replace_existing=True,
            )

        # Daily version check — 10:00
        self._scheduler.add_job(
            self._check_for_updates,
            trigger=CronTrigger(hour=10, minute=0, timezone=self._tz_name),
            id="version_check",
            replace_existing=True,
        )

        # Check reminders — every 60 seconds
        if self._reminders is not None:
            self._scheduler.add_job(
                self._check_reminders,
                trigger=IntervalTrigger(seconds=60),
                id="check_reminders",
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

    async def _check_reminders(self) -> None:
        """Fire due reminders — message, call, or both."""
        if self._reminders is None:
            return

        due = self._reminders.get_due()
        if not due:
            return

        for r in due:
            rid = r["id"]
            msg = r["message"]
            delivery = r.get("delivery", "message")
            user_id = r["user_id"]

            log.info("Firing reminder #%d: '%s' (%s)", rid, msg[:40], delivery)

            # --- Telegram message ---
            if delivery in ("message", "both"):
                try:
                    if self._tg_bot:
                        await self._tg_bot.send_message(
                            chat_id=user_id,
                            text=f"\u23f0 *Reminder*\n\n{msg}",
                            parse_mode="Markdown",
                        )
                except Exception as e:
                    log.error("Reminder #%d message failed: %s", rid, e)

            # --- Voice call ---
            if delivery in ("call", "both"):
                try:
                    agent = self._agent
                    if agent and getattr(agent, "caller", None) and getattr(agent, "tts", None):
                        from pathlib import Path
                        import asyncio
                        audio_dir = Path("/opt/kovo/data/audio")
                        audio_dir.mkdir(parents=True, exist_ok=True)
                        mp3 = str(audio_dir / f"reminder_{rid}.mp3")
                        await agent.tts.speak(msg[:500], mp3)
                        try:
                            await agent.caller.call(user_id, mp3, timeout=30)
                        except Exception as call_err:
                            log.warning("Reminder #%d call failed, sending voice msg: %s", rid, call_err)
                            if self._tg_bot:
                                try:
                                    await self._tg_bot.send_voice(
                                        chat_id=user_id,
                                        voice=open(mp3, "rb"),
                                        caption=f"\u23f0 Reminder: {msg[:200]}",
                                    )
                                except Exception:
                                    pass
                    elif self._tg_bot:
                        # No caller configured — fall back to message
                        await self._tg_bot.send_message(
                            chat_id=user_id,
                            text=f"\U0001f4de *Reminder (call unavailable)*\n\n{msg}",
                            parse_mode="Markdown",
                        )
                except Exception as e:
                    log.error("Reminder #%d call delivery failed: %s", rid, e)

            self._reminders.mark_done(rid)
            log.info("Reminder #%d delivered and marked done", rid)

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
