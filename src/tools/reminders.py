"""
Smart reminder system — SQLite-backed with message + voice call delivery.

The agent creates reminders by outputting [SET_REMINDER: ...] tags.
A scheduler job checks every 60 seconds and fires due reminders
via Telegram message, voice call, or both.
"""
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from src.utils.platform import data_path

log = logging.getLogger(__name__)

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS reminders (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    message     TEXT    NOT NULL,
    due_at      TEXT    NOT NULL,
    delivery    TEXT    DEFAULT 'message',
    status      TEXT    DEFAULT 'pending',
    created_at  TEXT    NOT NULL
)
"""


class ReminderManager:
    """Manages reminders in SQLite. Thread-safe via per-call connections."""

    def __init__(self, db_path: Path | str | None = None):
        self.db_path = str(db_path or (data_path() / "kovo.db"))
        self._init_table()

    def _conn(self) -> sqlite3.Connection:
        c = sqlite3.connect(self.db_path)
        c.row_factory = sqlite3.Row
        return c

    def _init_table(self):
        try:
            c = self._conn()
            c.execute(_CREATE_TABLE)
            c.commit()
            c.close()
            log.info("Reminders table ready")
        except Exception as e:
            log.error("Reminders table init failed: %s", e)

    def create(self, user_id: int, message: str, due_at: str,
               delivery: str = "message") -> int:
        """Create a reminder. Returns the reminder ID. Raises ValueError for invalid dates."""
        from datetime import datetime as _dt
        # Validate ISO date format — reject garbage that would fire immediately
        try:
            parsed = _dt.fromisoformat(due_at)
            # Normalize to consistent format
            due_at = parsed.strftime("%Y-%m-%dT%H:%M")
        except (ValueError, TypeError):
            raise ValueError(f"Invalid reminder date: {due_at!r} — use ISO format like 2026-03-30T15:00")
        from src.utils.tz import now
        c = self._conn()
        cur = c.execute(
            "INSERT INTO reminders (user_id, message, due_at, delivery, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, message, due_at, delivery, now().isoformat()),
        )
        c.commit()
        rid = cur.lastrowid
        c.close()
        log.info("Reminder #%d created: '%s' at %s (%s)",
                 rid, message[:40], due_at, delivery)
        return rid

    def get_due(self) -> list[dict]:
        """Return all pending reminders whose due_at <= now."""
        from src.utils.tz import now
        current = now().strftime("%Y-%m-%dT%H:%M")
        c = self._conn()
        rows = c.execute(
            "SELECT * FROM reminders WHERE status='pending' AND due_at <= ?",
            (current,),
        ).fetchall()
        c.close()
        return [dict(r) for r in rows]

    def mark_done(self, reminder_id: int):
        c = self._conn()
        c.execute("UPDATE reminders SET status='done' WHERE id=?", (reminder_id,))
        c.commit()
        c.close()

    def list_pending(self, user_id: int) -> list[dict]:
        """List all pending reminders for a user, sorted by due date."""
        c = self._conn()
        rows = c.execute(
            "SELECT * FROM reminders WHERE user_id=? AND status='pending' "
            "ORDER BY due_at",
            (user_id,),
        ).fetchall()
        c.close()
        return [dict(r) for r in rows]

    def cancel(self, reminder_id: int, user_id: int) -> bool:
        """Cancel a pending reminder. Returns True if found and cancelled."""
        c = self._conn()
        cur = c.execute(
            "UPDATE reminders SET status='cancelled' "
            "WHERE id=? AND user_id=? AND status='pending'",
            (reminder_id, user_id),
        )
        c.commit()
        ok = cur.rowcount > 0
        c.close()
        if ok:
            log.info("Reminder #%d cancelled", reminder_id)
        return ok
