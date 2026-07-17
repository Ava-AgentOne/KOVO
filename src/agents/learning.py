"""
Auto-skill learning (v3.0 Phase 2) — Kovo drafts skills from what it does.

When the owner keeps asking about a topic (TOPIC_THRESHOLD hits on the
agent's existing topic tracker) and no installed skill covers it, the
learner drafts a SKILL.md via the brain and queues it for OWNER APPROVAL —
Telegram inline buttons and a dashboard pending queue. Nothing ever
self-activates; a rejected proposal is never re-proposed; at most
DAILY_CAP proposals per day.

Pending proposals live in SQLite (kovo.db). Approval writes the skill via
the existing SkillCreator (hot-reloads the registry) and records
provenance — learned skills carry a badge on the dashboard.
"""
from __future__ import annotations

import json
import logging
import re
import sqlite3
from collections import deque
from pathlib import Path

from src.utils.platform import data_path

log = logging.getLogger(__name__)

TOPIC_THRESHOLD = 3     # topic mentions before proposing
DAILY_CAP = 2           # proposals per day, max
RECENT_KEPT = 3         # exchanges remembered per topic for drafting

_CREATE = """
CREATE TABLE IF NOT EXISTS pending_skills (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    topic       TEXT    NOT NULL,
    name        TEXT    NOT NULL,
    description TEXT    NOT NULL,
    triggers    TEXT    NOT NULL,
    body        TEXT    NOT NULL,
    status      TEXT    DEFAULT 'pending',
    created_at  TEXT    NOT NULL,
    decided_at  TEXT
)
"""

_DRAFT_SYSTEM = (
    "You are drafting a reusable SKILL.md for the KOVO agent. Reply with "
    "STRICT JSON only — no prose, no code fences — with exactly these keys:\n"
    '{"name": "kebab-case-name", "description": "one line, max 100 chars", '
    '"triggers": ["5-10 keyword strings"], '
    '"body": "markdown procedure: ## When triggered, numbered steps, edge cases"}\n'
    "The skill must capture the PROCEDURE (how to accomplish the task), not "
    "the specific answers from the conversation."
)


def _parse_draft(text: str) -> dict | None:
    """Extract and validate the draft JSON from a model reply."""
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    name = re.sub(r"[^a-z0-9-]+", "-", str(d.get("name", "")).lower()).strip("-")
    triggers = [str(t).strip() for t in d.get("triggers", []) if str(t).strip()]
    body = str(d.get("body", "")).strip()
    desc = str(d.get("description", "")).strip()[:150]
    if not (name and desc and triggers and body):
        return None
    return {"name": name, "description": desc, "triggers": triggers, "body": body}


class SkillLearner:
    def __init__(self, router, skills, creator, db_path: Path | str | None = None):
        self.router = router
        self.skills = skills
        self.creator = creator
        self.db_path = str(db_path or (data_path() / "kovo.db"))
        self._recent: dict[str, deque] = {}
        self.notify = None      # async callable(pending_dict), wired by gateway
        self._init_table()

    def _conn(self) -> sqlite3.Connection:
        c = sqlite3.connect(self.db_path)
        c.row_factory = sqlite3.Row
        return c

    def _init_table(self):
        try:
            c = self._conn()
            c.execute(_CREATE)
            c.commit()
            c.close()
        except Exception as e:
            log.error("pending_skills table init failed: %s", e)

    # ── Observation (called from agent.handle) ────────────────────────────

    def remember(self, message: str, reply: str) -> None:
        """Keep recent exchanges per matched topic as drafting context."""
        from src.agents.kovo import _TOPIC_KEYWORDS
        msg_lower = message.lower()
        snippet = f"Owner: {message[:400]}\nKovo: {reply[:800]}"
        for topic, keywords in _TOPIC_KEYWORDS.items():
            if any(kw in msg_lower for kw in keywords):
                self._recent.setdefault(topic, deque(maxlen=RECENT_KEPT)).append(snippet)

    def should_propose(self, counter) -> str | None:
        """Pure decision: which topic (if any) deserves a proposal now."""
        if not counter:
            return None
        from src.agents.kovo import _TOPIC_KEYWORDS
        for topic, count in counter.items():
            if count < TOPIC_THRESHOLD:
                continue
            if self._topic_already_proposed(topic):
                continue
            # An installed skill already covering the topic's keywords wins
            probe = " ".join(_TOPIC_KEYWORDS.get(topic, [topic]))
            if self.skills.match_best(probe) is not None:
                continue
            if self._proposals_today() >= DAILY_CAP:
                return None
            return topic
        return None

    def _topic_already_proposed(self, topic: str) -> bool:
        c = self._conn()
        row = c.execute(
            "SELECT 1 FROM pending_skills WHERE topic=? LIMIT 1", (topic,)
        ).fetchone()
        c.close()
        return row is not None

    def _proposals_today(self) -> int:
        from src.utils.tz import now
        day = now().strftime("%Y-%m-%d")
        c = self._conn()
        n = c.execute(
            "SELECT COUNT(*) FROM pending_skills WHERE created_at LIKE ?",
            (day + "%",),
        ).fetchone()[0]
        c.close()
        return n

    # ── Drafting ──────────────────────────────────────────────────────────

    async def propose(self, topic: str) -> dict | None:
        """Draft a skill for the topic via the brain, queue it, notify."""
        context = "\n\n".join(self._recent.get(topic, [])) or f"Topic: {topic}"
        prompt = (
            f"Recent conversations about '{topic.replace('_', ' ')}':\n\n"
            f"{context}\n\nDraft the SKILL.md JSON now."
        )
        try:
            result = await self.router.route(
                prompt, system_prompt=_DRAFT_SYSTEM, force_complexity="medium",
            )
            draft = _parse_draft(result.get("text", ""))
        except Exception as e:
            log.error("Skill draft for %r failed: %s", topic, e)
            return None
        if draft is None:
            log.warning("Skill draft for %r unparseable — skipped", topic)
            return None
        if self.skills.get(draft["name"]) is not None:
            log.info("Skill %r already exists — proposal skipped", draft["name"])
            return None

        from src.utils.tz import now
        c = self._conn()
        cur = c.execute(
            "INSERT INTO pending_skills (topic, name, description, triggers,"
            " body, created_at) VALUES (?,?,?,?,?,?)",
            (topic, draft["name"], draft["description"],
             json.dumps(draft["triggers"]), draft["body"],
             now().isoformat(timespec="seconds")),
        )
        c.commit()
        pid = cur.lastrowid
        c.close()
        pending = self.get(pid)
        log.info("Skill proposal #%d %r queued (topic %r)", pid, draft["name"], topic)
        if self.notify is not None:
            try:
                await self.notify(pending)
            except Exception as e:
                log.error("Skill proposal notify failed: %s", e)
        return pending

    # ── Decisions ─────────────────────────────────────────────────────────

    def pending(self) -> list[dict]:
        c = self._conn()
        rows = c.execute(
            "SELECT * FROM pending_skills WHERE status='pending' ORDER BY id"
        ).fetchall()
        c.close()
        return [dict(r) for r in rows]

    def get(self, pid: int) -> dict | None:
        c = self._conn()
        row = c.execute("SELECT * FROM pending_skills WHERE id=?", (pid,)).fetchone()
        c.close()
        return dict(row) if row else None

    def _decide(self, pid: int, status: str) -> dict | None:
        p = self.get(pid)
        if not p or p["status"] != "pending":
            return None
        from src.utils.tz import now
        c = self._conn()
        c.execute(
            "UPDATE pending_skills SET status=?, decided_at=? WHERE id=?",
            (status, now().isoformat(timespec="seconds"), pid),
        )
        c.commit()
        c.close()
        return p

    def approve(self, pid: int):
        """Owner said yes — write the skill for real. Returns the Skill."""
        p = self._decide(pid, "approved")
        if p is None:
            raise ValueError("Proposal not found or already decided.")
        skill = self.creator.create(
            name=p["name"], description=p["description"], tools=[],
            triggers=json.loads(p["triggers"]), body=p["body"],
        )
        log.info("Skill %r LEARNED (proposal #%d approved)", p["name"], pid)
        return skill

    def reject(self, pid: int) -> bool:
        return self._decide(pid, "rejected") is not None

    def learned_names(self) -> set[str]:
        c = self._conn()
        rows = c.execute(
            "SELECT name FROM pending_skills WHERE status='approved'"
        ).fetchall()
        c.close()
        return {r["name"] for r in rows}
