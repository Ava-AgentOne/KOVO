"""
SQLite structured storage for Kovo.
WAL mode, 4 system tables: memories, heartbeat_log, permission_log, conversation_stats.
Natural language SELECT-only queries via Claude haiku.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from src.utils.platform import kovo_dir

log = logging.getLogger(__name__)

_DUBAI_TZ = timezone(timedelta(hours=4))
_DB_PATH = Path(str(kovo_dir()) + "/data/kovo.db")

_SCHEMA = """\
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS memories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    content     TEXT    NOT NULL,
    category    TEXT    NOT NULL DEFAULT 'general',
    source      TEXT    NOT NULL DEFAULT 'manual',
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    hash        TEXT    UNIQUE
);

CREATE TABLE IF NOT EXISTS heartbeat_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    check_type  TEXT    NOT NULL,
    status      TEXT    NOT NULL,
    alerts      TEXT,
    recorded_at TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS permission_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    action      TEXT    NOT NULL,
    pattern     TEXT    NOT NULL,
    command     TEXT,
    recorded_at TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS conversation_stats (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date        TEXT    NOT NULL UNIQUE,
    messages    INTEGER DEFAULT 0,
    tokens_in   INTEGER DEFAULT 0,
    tokens_out  INTEGER DEFAULT 0,
    models      TEXT
);
"""


class StructuredStore:
    """SQLite store with WAL mode, 4 system tables, and natural-language SELECT queries."""

    def __init__(self, db_path: Path = _DB_PATH):
        self.db_path = db_path
        self._conn: sqlite3.Connection | None = None
        self._init()

    # ── Init ──────────────────────────────────────────────────────────────

    def _init(self) -> None:
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = self._get_conn()
            conn.executescript(_SCHEMA)
            conn.commit()
            log.info("StructuredStore ready at %s", self.db_path)
        except Exception as e:
            log.error("StructuredStore init failed: %s", e)

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    # ── Core SQL ──────────────────────────────────────────────────────────

    def execute(self, sql: str, params: tuple = ()) -> list[dict]:
        """
        Execute SQL. SELECT returns rows as dicts.
        INSERT/UPDATE/DELETE returns [{"affected": rowcount}].
        """
        try:
            conn = self._get_conn()
            cur = conn.execute(sql, params)
            if sql.strip().upper().startswith("SELECT"):
                return [dict(row) for row in cur.fetchall()]
            conn.commit()
            return [{"affected": cur.rowcount}]
        except Exception as e:
            log.error("execute failed: %s | SQL: %s", e, sql[:200])
            raise

    def insert(self, table: str, data: dict) -> int:
        """Insert a row (OR IGNORE on conflict). Returns lastrowid."""
        cols = ", ".join(data.keys())
        placeholders = ", ".join("?" for _ in data)
        sql = f"INSERT OR IGNORE INTO {table} ({cols}) VALUES ({placeholders})"
        try:
            conn = self._get_conn()
            cur = conn.execute(sql, tuple(data.values()))
            conn.commit()
            return cur.lastrowid or 0
        except Exception as e:
            log.error("insert into %s failed: %s", table, e)
            return 0

    # ── Natural language query ─────────────────────────────────────────────

    def natural_query(self, question: str) -> str:
        """
        Translate a natural language question to SQL via Claude haiku, execute it,
        and return a formatted text result. Only SELECT is allowed.
        """
        schema = self.get_schema()
        prompt = (
            f"You are a SQLite expert. Given this schema:\n\n{schema}\n\n"
            f"Translate this question to a single SQLite SELECT query:\n{question}\n\n"
            "Reply with ONLY the raw SQL — no markdown, no explanation, no backticks."
        )
        try:
            from src.tools.claude_cli import call_claude, extract_text
            response = call_claude(prompt, model="haiku")
            sql = extract_text(response).strip().rstrip(";")
            if not sql.upper().startswith("SELECT"):
                return "❌ Only SELECT queries are allowed."
            rows = self.execute(sql)
            if not rows:
                return "No results found."
            headers = list(rows[0].keys())
            sep = " | "
            lines = [sep.join(headers)]
            lines.append("-" * len(lines[0]))
            for row in rows[:50]:
                lines.append(sep.join(str(row.get(h, "")) for h in headers))
            if len(rows) > 50:
                lines.append(f"… ({len(rows) - 50} more rows)")
            return "\n".join(lines)
        except Exception as e:
            log.error("natural_query failed: %s", e)
            return f"❌ Query failed: {e}"

    # ── Schema ────────────────────────────────────────────────────────────

    def get_schema(self) -> str:
        """Return a compact schema description for system prompts and query translation."""
        try:
            tables = self.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            lines = []
            for t in tables:
                name = t["name"]
                cols = self.execute(f"PRAGMA table_info({name})")
                col_str = ", ".join(f"{c['name']} {c['type']}" for c in cols)
                lines.append(f"  {name}({col_str})")
            return "Tables:\n" + "\n".join(lines) if lines else "(no tables)"
        except Exception as e:
            return f"(schema unavailable: {e})"

    # ── Custom tables ─────────────────────────────────────────────────────

    def create_custom_table(self, table_name: str, columns: list[str]) -> bool:
        """
        Create a user-defined table. Enforces `user_` prefix.
        columns: ["col1 TEXT", "col2 INTEGER", ...]
        """
        if not table_name.startswith("user_"):
            table_name = f"user_{table_name}"
        col_defs = ", ".join(columns)
        sql = (
            f"CREATE TABLE IF NOT EXISTS {table_name} "
            f"(id INTEGER PRIMARY KEY AUTOINCREMENT, {col_defs}, "
            f"created_at TEXT DEFAULT (datetime('now')))"
        )
        try:
            conn = self._get_conn()
            conn.execute(sql)
            conn.commit()
            log.info("Created custom table: %s", table_name)
            return True
        except Exception as e:
            log.error("create_custom_table failed: %s", e)
            return False

    # ── Convenience writers ───────────────────────────────────────────────

    def log_heartbeat(self, check_type: str, status: str, alerts: list[str] | None = None) -> None:
        """Log a heartbeat check result to heartbeat_log."""
        self.insert("heartbeat_log", {
            "check_type": check_type,
            "status": status,
            "alerts": json.dumps(alerts) if alerts else None,
            "recorded_at": datetime.now(_DUBAI_TZ).strftime("%Y-%m-%d %H:%M:%S"),
        })

    def log_permission(self, action: str, pattern: str, command: str | None = None) -> None:
        """Log a permission approve/deny to permission_log."""
        self.insert("permission_log", {
            "action": action,
            "pattern": pattern,
            "command": command,
            "recorded_at": datetime.now(_DUBAI_TZ).strftime("%Y-%m-%d %H:%M:%S"),
        })

    def increment_conversation_stats(
        self,
        date_str: str,
        messages: int = 1,
        tokens_in: int = 0,
        tokens_out: int = 0,
        model: str | None = None,
    ) -> None:
        """Upsert conversation stats for a given date."""
        conn = self._get_conn()
        try:
            existing = self.execute(
                "SELECT * FROM conversation_stats WHERE date = ?", (date_str,)
            )
            if existing:
                row = existing[0]
                models = json.loads(row.get("models") or "{}")
                if model:
                    models[model] = models.get(model, 0) + 1
                conn.execute(
                    "UPDATE conversation_stats "
                    "SET messages=messages+?, tokens_in=tokens_in+?, "
                    "tokens_out=tokens_out+?, models=? WHERE date=?",
                    (messages, tokens_in, tokens_out, json.dumps(models), date_str),
                )
            else:
                models = {model: 1} if model else {}
                conn.execute(
                    "INSERT INTO conversation_stats (date, messages, tokens_in, tokens_out, models) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (date_str, messages, tokens_in, tokens_out, json.dumps(models)),
                )
            conn.commit()
        except Exception as e:
            log.error("increment_conversation_stats failed: %s", e)

    def get_memory_stats(self) -> dict:
        """Return summary stats for the memories table."""
        try:
            total = self.execute("SELECT COUNT(*) AS n FROM memories")[0]["n"]
            by_source = self.execute(
                "SELECT source, COUNT(*) AS n FROM memories GROUP BY source"
            )
            by_cat = self.execute(
                "SELECT category, COUNT(*) AS n FROM memories "
                "GROUP BY category ORDER BY n DESC LIMIT 10"
            )
            return {
                "total": total,
                "by_source": {r["source"]: r["n"] for r in by_source},
                "top_categories": {r["category"]: r["n"] for r in by_cat},
            }
        except Exception as e:
            return {"error": str(e)}
