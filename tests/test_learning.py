"""
Auto-skill learning tests (v3.0 Phase 2) — detection heuristics, draft
parsing, pending queue, approval flow. Fake router/skills/creator; no brain.
"""
import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.agents.learning import DAILY_CAP, SkillLearner, _parse_draft


class TestParseDraft:
    GOOD = json.dumps({
        "name": "Server Health Check!",
        "description": "Check server health quickly",
        "triggers": ["health", "server check", ""],
        "body": "## When triggered\n1. Run checks",
    })

    def test_valid_json_normalized(self):
        d = _parse_draft(f"Sure! Here it is:\n{self.GOOD}")
        assert d["name"] == "server-health-check"      # kebab-cased
        assert d["triggers"] == ["health", "server check"]  # empties dropped
        assert d["body"].startswith("## When triggered")

    def test_garbage_returns_none(self):
        assert _parse_draft("no json here") is None
        assert _parse_draft('{"name": "x"}') is None    # missing keys


def _insert_proposal(lr, topic, name, status="pending"):
    """Insert a proposal row directly (test setup shortcut)."""
    import sqlite3
    from src.utils.tz import now
    c = sqlite3.connect(lr.db_path)
    c.execute(
        "INSERT INTO pending_skills (topic, name, description, triggers, body,"
        " status, created_at) VALUES (?,?,?,?,?,?,?)",
        (topic, name, "d", "[]", "b", status, now().isoformat(timespec="seconds")),
    )
    c.commit()
    c.close()


def _learner(tmp_path, skills_match=None, skill_exists=None):
    router = MagicMock()
    skills = MagicMock()
    skills.match_best = MagicMock(return_value=skills_match)
    skills.get = MagicMock(return_value=skill_exists)
    creator = MagicMock()
    creator.create = MagicMock(
        side_effect=lambda **kw: SimpleNamespace(name=kw["name"])
    )
    return SkillLearner(router=router, skills=skills, creator=creator,
                        db_path=tmp_path / "test.db")


class TestShouldPropose:
    def test_below_threshold_no(self, tmp_path):
        lr = _learner(tmp_path)
        assert lr.should_propose({"server_management": 2}) is None
        assert lr.should_propose(None) is None

    def test_threshold_proposes(self, tmp_path):
        lr = _learner(tmp_path)
        assert lr.should_propose({"server_management": 3}) == "server_management"

    def test_existing_skill_blocks(self, tmp_path):
        lr = _learner(tmp_path, skills_match=SimpleNamespace(name="covered"))
        assert lr.should_propose({"server_management": 5}) is None

    def test_already_proposed_topic_blocks(self, tmp_path):
        lr = _learner(tmp_path)
        _insert_proposal(lr, "server_management", "x")
        assert lr.should_propose({"server_management": 9}) is None

    def test_daily_cap(self, tmp_path):
        lr = _learner(tmp_path)
        for i in range(DAILY_CAP):
            _insert_proposal(lr, f"topic{i}", f"skill{i}")
        assert lr.should_propose({"server_management": 5}) is None


class TestProposeAndDecide:
    DRAFT = json.dumps({
        "name": "email-triage", "description": "Sort the inbox",
        "triggers": ["email", "inbox"], "body": "## Steps\n1. Read",
    })

    def test_propose_inserts_and_notifies(self, tmp_path):
        lr = _learner(tmp_path)
        lr.router.route = AsyncMock(return_value={"text": self.DRAFT})
        notified = []
        async def notify(p): notified.append(p["name"])
        lr.notify = notify
        p = asyncio.run(lr.propose("email_management"))
        assert p["name"] == "email-triage" and p["status"] == "pending"
        assert notified == ["email-triage"]
        assert len(lr.pending()) == 1

    def test_unparseable_draft_skipped(self, tmp_path):
        lr = _learner(tmp_path)
        lr.router.route = AsyncMock(return_value={"text": "I refuse to JSON"})
        assert asyncio.run(lr.propose("email_management")) is None
        assert lr.pending() == []

    def test_approve_creates_skill_once(self, tmp_path):
        lr = _learner(tmp_path)
        lr.router.route = AsyncMock(return_value={"text": self.DRAFT})
        p = asyncio.run(lr.propose("email_management"))
        skill = lr.approve(p["id"])
        assert skill.name == "email-triage"
        lr.creator.create.assert_called_once()
        assert "email-triage" in lr.learned_names()
        assert lr.pending() == []
        with pytest.raises(ValueError):      # double-approve blocked
            lr.approve(p["id"])

    def test_reject_never_activates(self, tmp_path):
        lr = _learner(tmp_path)
        lr.router.route = AsyncMock(return_value={"text": self.DRAFT})
        p = asyncio.run(lr.propose("email_management"))
        assert lr.reject(p["id"]) is True
        lr.creator.create.assert_not_called()
        assert lr.learned_names() == set()
        assert lr.reject(p["id"]) is False   # already decided
