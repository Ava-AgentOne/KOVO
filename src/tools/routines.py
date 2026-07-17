"""
Kovo Routines (v3.0 Phase 1) — user-defined recurring autonomous tasks.

A routine is a stored prompt on a cron schedule: "every weekday at 07:00,
check my email and brief me". The heartbeat scheduler checks every 60s for
due routines, runs each through the agent, and delivers the result via the
owner's channel.

SQLite-backed (same kovo.db as reminders, per-call connections). Cron
validation and next-run computation use APScheduler's CronTrigger — the
same engine that ultimately won't run them, but the same syntax.

Each routine runs under its own synthetic user_id (-(1000+id)) so it keeps
its OWN brain session across runs — "alert me if anything changed since
last time" works — without polluting the owner's chat session.
"""
from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from src.utils.platform import data_path

log = logging.getLogger(__name__)

_CREATE_ROUTINES = """
CREATE TABLE IF NOT EXISTS routines (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL,
    name          TEXT    NOT NULL UNIQUE,
    prompt        TEXT    NOT NULL,
    cron          TEXT    NOT NULL,
    schedule_text TEXT    DEFAULT '',
    delivery      TEXT    DEFAULT 'message',
    enabled       INTEGER DEFAULT 1,
    created_at    TEXT    NOT NULL,
    next_run      TEXT,
    last_run      TEXT,
    last_status   TEXT,
    last_result   TEXT
)
"""

_CREATE_RUNS = """
CREATE TABLE IF NOT EXISTS routine_runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    routine_id  INTEGER NOT NULL,
    started_at  TEXT    NOT NULL,
    duration_s  REAL,
    status      TEXT,
    result      TEXT
)
"""

RUNS_KEPT = 20          # history retained per routine
DELIVERIES = ("message", "silent")   # silent = log/history only


def _now_minute() -> str:
    from src.utils.tz import now
    return now().strftime("%Y-%m-%dT%H:%M")


def next_fire(cron: str, after=None) -> str:
    """Next fire time for a 5-field cron expression, as ISO minute string.
    Raises ValueError on invalid cron."""
    from apscheduler.triggers.cron import CronTrigger
    from src.utils.tz import get_tz, now
    try:
        trigger = CronTrigger.from_crontab(cron, timezone=get_tz())
    except ValueError as e:
        raise ValueError(f"Invalid cron expression {cron!r}: {e}")
    base = after or now()
    nxt = trigger.get_next_fire_time(None, base)
    if nxt is None:
        raise ValueError(f"Cron {cron!r} never fires")
    return nxt.strftime("%Y-%m-%dT%H:%M")


class RoutineManager:
    """Thread-safe via per-call connections, like ReminderManager."""

    def __init__(self, db_path: Path | str | None = None):
        self.db_path = str(db_path or (data_path() / "kovo.db"))
        self._init_tables()

    def _conn(self) -> sqlite3.Connection:
        c = sqlite3.connect(self.db_path)
        c.row_factory = sqlite3.Row
        return c

    def _init_tables(self):
        try:
            c = self._conn()
            c.execute(_CREATE_ROUTINES)
            c.execute(_CREATE_RUNS)
            c.commit()
            c.close()
        except Exception as e:
            log.error("Routines tables init failed: %s", e)

    # ── CRUD ──────────────────────────────────────────────────────────────

    def create(self, user_id: int, name: str, prompt: str, cron: str,
               schedule_text: str = "", delivery: str = "message") -> int:
        name = name.strip()
        prompt = prompt.strip()
        if not name or not prompt:
            raise ValueError("Routine needs a name and a prompt.")
        if delivery not in DELIVERIES:
            raise ValueError(f"delivery must be one of: {', '.join(DELIVERIES)}")
        nxt = next_fire(cron)   # validates cron too
        from src.utils.tz import now
        c = self._conn()
        try:
            cur = c.execute(
                "INSERT INTO routines (user_id, name, prompt, cron, schedule_text,"
                " delivery, created_at, next_run) VALUES (?,?,?,?,?,?,?,?)",
                (user_id, name, prompt, cron, schedule_text, delivery,
                 now().isoformat(timespec="seconds"), nxt),
            )
            c.commit()
            rid = cur.lastrowid
        except sqlite3.IntegrityError:
            raise ValueError(f"A routine named {name!r} already exists.")
        finally:
            c.close()
        log.info("Routine #%d created: %r cron=%r next=%s", rid, name, cron, nxt)
        return rid

    def list_all(self) -> list[dict]:
        c = self._conn()
        rows = c.execute(
            "SELECT * FROM routines ORDER BY enabled DESC, next_run"
        ).fetchall()
        c.close()
        return [dict(r) for r in rows]

    def get(self, rid: int) -> dict | None:
        c = self._conn()
        row = c.execute("SELECT * FROM routines WHERE id=?", (rid,)).fetchone()
        c.close()
        return dict(row) if row else None

    def get_by_name(self, name: str) -> dict | None:
        c = self._conn()
        row = c.execute(
            "SELECT * FROM routines WHERE lower(name)=lower(?)", (name.strip(),)
        ).fetchone()
        c.close()
        return dict(row) if row else None

    def set_enabled(self, rid: int, enabled: bool) -> bool:
        r = self.get(rid)
        if not r:
            return False
        # Re-enabling recomputes next_run so a long-disabled routine doesn't
        # fire immediately on a stale timestamp.
        nxt = next_fire(r["cron"]) if enabled else r["next_run"]
        c = self._conn()
        c.execute("UPDATE routines SET enabled=?, next_run=? WHERE id=?",
                  (1 if enabled else 0, nxt, rid))
        c.commit()
        c.close()
        return True

    def delete(self, rid: int) -> bool:
        c = self._conn()
        cur = c.execute("DELETE FROM routines WHERE id=?", (rid,))
        c.execute("DELETE FROM routine_runs WHERE routine_id=?", (rid,))
        c.commit()
        ok = cur.rowcount > 0
        c.close()
        return ok

    # ── Execution support ─────────────────────────────────────────────────

    def due(self, now_iso: str | None = None) -> list[dict]:
        now_iso = now_iso or _now_minute()
        c = self._conn()
        rows = c.execute(
            "SELECT * FROM routines WHERE enabled=1 AND next_run <= ? "
            "ORDER BY next_run", (now_iso,),
        ).fetchall()
        c.close()
        return [dict(r) for r in rows]

    def record_run(self, rid: int, status: str, result: str,
                   duration_s: float) -> None:
        r = self.get(rid)
        if not r:
            return
        from src.utils.tz import now
        started = now().isoformat(timespec="seconds")
        preview = (result or "")[:1000]
        try:
            nxt = next_fire(r["cron"])
        except ValueError:
            nxt = None   # cron somehow invalid now — routine stops firing
        c = self._conn()
        c.execute(
            "UPDATE routines SET last_run=?, last_status=?, last_result=?,"
            " next_run=? WHERE id=?",
            (started, status, preview, nxt, rid),
        )
        c.execute(
            "INSERT INTO routine_runs (routine_id, started_at, duration_s,"
            " status, result) VALUES (?,?,?,?,?)",
            (rid, started, round(duration_s, 1), status, preview),
        )
        c.execute(
            "DELETE FROM routine_runs WHERE routine_id=? AND id NOT IN "
            "(SELECT id FROM routine_runs WHERE routine_id=? "
            " ORDER BY id DESC LIMIT ?)",
            (rid, rid, RUNS_KEPT),
        )
        c.commit()
        c.close()

    def runs(self, rid: int, limit: int = 10) -> list[dict]:
        c = self._conn()
        rows = c.execute(
            "SELECT * FROM routine_runs WHERE routine_id=? "
            "ORDER BY id DESC LIMIT ?", (rid, limit),
        ).fetchall()
        c.close()
        return [dict(r) for r in rows]
