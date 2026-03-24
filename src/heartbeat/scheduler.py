"""
Heartbeat scheduler — APScheduler cron-based periodic health checks.
Reads intervals from HEARTBEAT.md (falling back to config defaults).
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

_DUBAI_TZ = timezone(timedelta(hours=4))


def _dubai_today() -> date:
    return datetime.now(_DUBAI_TZ).date()
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from src.heartbeat.checks import check_thresholds, fetch_weather, gather_full_health, gather_quick_health
from src.heartbeat.reporter import HeartbeatReporter
from src.memory.manager import MemoryManager
from src.tools.ollama import OllamaClient

log = logging.getLogger(__name__)

# Tracking file for the 80-day SIM reminder
_SIM_REMINDER_FILE = Path("/opt/miniclaw/data/.sim_reminder_sent")


class HeartbeatScheduler:
    def __init__(
        self,
        reporter: HeartbeatReporter,
        ollama: OllamaClient,
        memory: MemoryManager,
        quick_interval_minutes: int = 30,
        full_interval_hours: int = 6,
        morning_time: str = "08:00",
        storage=None,        # StorageManager — optional, avoids circular import
        auto_extractor=None, # AutoMemoryExtractor — optional
    ):
        self.reporter = reporter
        self.ollama = ollama
        self.memory = memory
        self.storage = storage
        self.auto_extractor = auto_extractor
        self.quick_interval = quick_interval_minutes
        self.full_interval = full_interval_hours
        self.morning_hour, self.morning_minute = (
            int(x) for x in morning_time.split(":")
        )
        self._scheduler = AsyncIOScheduler(timezone="Asia/Dubai")
        self._started = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        if self._started:
            return

        # Quick check every N minutes
        self._scheduler.add_job(
            self._quick_check,
            trigger=IntervalTrigger(minutes=self.quick_interval),
            id="quick_check",
            replace_existing=True,
            misfire_grace_time=60,
        )

        # Full report every N hours
        self._scheduler.add_job(
            self._full_report,
            trigger=IntervalTrigger(hours=self.full_interval),
            id="full_report",
            replace_existing=True,
            misfire_grace_time=300,
        )

        # Morning briefing — daily at configured time (Asia/Dubai)
        self._scheduler.add_job(
            self._morning_briefing,
            trigger=CronTrigger(
                hour=self.morning_hour,
                minute=self.morning_minute,
                timezone="Asia/Dubai",
            ),
            id="morning_briefing",
            replace_existing=True,
        )

        # SIM reminder — check daily at 09:00
        self._scheduler.add_job(
            self._sim_reminder_check,
            trigger=CronTrigger(hour=9, minute=0, timezone="Asia/Dubai"),
            id="sim_reminder",
            replace_existing=True,
        )

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
            # Weekly memory consolidation + budget check — Sunday 03:30
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

        # Storage GC — every 6 hours alongside the full health check
        if self.storage is not None:
            self._scheduler.add_job(
                self._storage_check,
                trigger=IntervalTrigger(hours=self.full_interval),
                id="storage_check",
                replace_existing=True,
                misfire_grace_time=300,
            )
            # Weekly storage review — Sunday 03:00 Asia/Dubai
            self._scheduler.add_job(
                self._storage_review,
                trigger=CronTrigger(
                    day_of_week="sun",
                    hour=3,
                    minute=0,
                    timezone="Asia/Dubai",
                ),
                id="storage_review",
                replace_existing=True,
            )

        self._scheduler.start()
        self._started = True
        log.info(
            "Heartbeat scheduler started: quick=%dmin full=%dh morning=%02d:%02d",
            self.quick_interval, self.full_interval,
            self.morning_hour, self.morning_minute,
        )

    def stop(self) -> None:
        if self._started and self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            self._started = False
            log.info("Heartbeat scheduler stopped")

    # ------------------------------------------------------------------
    # Jobs
    # ------------------------------------------------------------------

    async def _quick_check(self) -> None:
        """Every 30 min: gather metrics, alert if thresholds breached."""
        log.debug("Running quick health check")
        try:
            health = gather_quick_health()
            alerts = check_thresholds(health)
            if alerts:
                alert_text = "\n".join(alerts)
                snippet = health[:600]
                await self.reporter.send_alert(
                    f"{alert_text}\n\n```\n{snippet}\n```"
                )
        except Exception as e:
            log.error("Quick check failed: %s", e)

    async def _full_report(self) -> None:
        """Every 6 hours: full health data, summarized by Ollama."""
        log.info("Running full health report")
        try:
            health = gather_full_health()
            alerts = check_thresholds(health)
            alert_prefix = ("\n".join(alerts) + "\n\n") if alerts else ""

            try:
                prompt = (
                    "Summarize this server health data concisely (3-5 bullet points) "
                    "for a sysadmin. Flag any concerns. If all is healthy, say so.\n\n"
                    f"{health[:2000]}"
                )
                summary = await self.ollama.generate(prompt)
            except Exception as e:
                log.warning("Ollama unavailable for full report (%s) — sending raw data", e)
                summary = f"_(Ollama offline — raw data below)_\n\n```\n{health[:1500]}\n```"

            await self.reporter.send_health_report(
                alert_prefix + summary,
                title="6-Hour Health Report",
            )
        except Exception as e:
            log.error("Full report failed: %s", e)

    async def _morning_briefing(self) -> None:
        """Daily at 8 AM: good morning + weather + health + yesterday summary."""
        log.info("Running morning briefing")
        try:
            health = gather_quick_health()
            weather = fetch_weather("Al Ain, UAE")
            yesterday = self.memory.daily_log(_dubai_today() - timedelta(days=1))
            yesterday_summary = yesterday[-800:] if yesterday else "No activity recorded."

            try:
                prompt = (
                    "Give a brief, friendly good morning briefing (3-5 bullet points) covering:\n"
                    f"1. Local weather (Al Ain, UAE): {weather}\n"
                    f"2. Server health: {health[:600]}\n"
                    f"3. Yesterday's activity: {yesterday_summary}\n\n"
                    "Be direct and concise. Flag any issues. "
                    "Always include the weather as the first bullet."
                )
                briefing = await self.ollama.generate(prompt)
            except Exception as e:
                log.warning("Ollama unavailable for morning briefing (%s) — sending raw data", e)
                briefing = (
                    f"🌤️ **Weather:** {weather}\n\n"
                    f"_(Ollama offline — raw data)_\n\n"
                    f"**Health:**\n```\n{health[:600]}\n```\n\n"
                    f"**Yesterday:**\n{yesterday_summary[:400]}"
                )

            await self.reporter.send_morning_briefing(briefing)
        except Exception as e:
            log.error("Morning briefing failed: %s", e)

    async def _sim_reminder_check(self) -> None:
        """Check if 80 days have passed since last SIM reminder."""
        today = _dubai_today()
        if _SIM_REMINDER_FILE.exists():
            try:
                last_sent = date.fromisoformat(_SIM_REMINDER_FILE.read_text().strip())
                if (today - last_sent).days < 80:
                    return
            except Exception:
                pass

        await self.reporter.send_sim_reminder()
        _SIM_REMINDER_FILE.parent.mkdir(parents=True, exist_ok=True)
        _SIM_REMINDER_FILE.write_text(today.isoformat())
        log.info("SIM reminder sent")

    async def _archive_logs(self) -> None:
        """Archive daily logs older than 30 days."""
        try:
            n = self.memory.archive_old_logs(days=30)
            if n:
                log.info("Archived %d old daily logs", n)
        except Exception as e:
            log.error("Log archival failed: %s", e)

    async def _auto_extract(self) -> None:
        """Daily 23:00: extract learnings from today's log into MEMORY.md + SQLite."""
        if self.auto_extractor is None:
            return
        log.info("Running auto-memory extraction")
        try:
            result = await self.auto_extractor.extract_and_store()
            log.info("Auto-extract: %s", result)
        except Exception as e:
            log.error("Auto-extract failed: %s", e)

    async def _weekly_memory_consolidation(self) -> None:
        """Sunday 03:30: enforce memory budget (archive if MEMORY.md > 500 lines)."""
        if self.auto_extractor is None:
            return
        log.info("Running weekly memory budget check")
        try:
            self.auto_extractor._check_memory_budget()
        except Exception as e:
            log.error("Weekly memory consolidation failed: %s", e)

    async def _storage_check(self) -> None:
        """Every 6 hours: auto-purge tier-1 files and alert on low disk."""
        if self.storage is None:
            return
        log.debug("Running storage check")
        try:
            from src.tools.storage import _NOTIFY_MIN_FREED
            result = self.storage.auto_purge()
            freed = result.get("freed_bytes", 0)
            if freed >= _NOTIFY_MIN_FREED:
                details = "\n".join(f"  • {d}" for d in result["details"])
                await self.reporter.send(
                    f"🗑️ *Auto-purge complete*\n\n"
                    f"Freed {freed / 1_048_576:.1f}MB\n{details}"
                )
            usage = self.storage.get_disk_usage()
            if usage["warning"]:
                alert = self.storage.build_low_disk_alert(usage)
                await self.reporter.send_alert(alert)
        except Exception as e:
            log.error("Storage check failed: %s", e)

    async def _storage_review(self) -> None:
        """Weekly Sunday 03:00: scan tier-2 files and ask Esam to approve cleanup."""
        if self.storage is None:
            return
        log.info("Running weekly storage review")
        try:
            purgeable = self.storage.scan_purgeable()
            if not purgeable:
                log.info("Storage review: nothing purgeable, skipping notification")
                return

            _ICONS = {"photos": "📸", "documents": "📄", "images": "🖼️"}
            lines = []
            for dir_name, info in purgeable.items():
                icon = _ICONS.get(dir_name, "📁")
                lines.append(
                    f"{icon} *{dir_name.capitalize()}*: "
                    f"{info['count']} files, {info['total_mb']}MB "
                    f"(older than 30 days)"
                )

            dir_list = "\n".join(lines)
            msg = (
                f"📦 *Storage Review*\n\n"
                f"Old files I can clean up (with your approval):\n\n"
                f"{dir_list}\n\n"
                f"Reply:\n"
                f"/purge all — delete everything listed\n"
                f"/purge photos — delete old photos only\n"
                f"/purge documents — delete old documents only\n"
                f"/purge images — delete old images only\n"
                f"/storage — see full disk report"
            )
            await self.reporter.send(msg)
        except Exception as e:
            log.error("Storage review failed: %s", e)

    # ------------------------------------------------------------------
    # Manual triggers (callable from Telegram commands)
    # ------------------------------------------------------------------

    async def run_quick_check_now(self) -> str:
        """Trigger a quick check and return the result as text."""
        health = gather_quick_health()
        alerts = check_thresholds(health)
        if alerts:
            return "\n".join(alerts) + "\n\n```\n" + health[:800] + "\n```"
        return "✅ All clear\n\n```\n" + health[:800] + "\n```"

    async def run_full_report_now(self) -> str:
        """Trigger a full report and return the result as text."""
        health = gather_full_health()
        alerts = check_thresholds(health)
        alert_prefix = ("\n".join(alerts) + "\n\n") if alerts else ""
        return alert_prefix + "```\n" + health[:2500] + "\n```"
