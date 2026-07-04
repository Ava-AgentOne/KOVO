"""
Mission Control tests (v2.1 Step 3) — busy state, activity parsing,
metrics history, and the dashboard-wide reminder helpers.
"""
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class TestBusyState:
    def test_set_get_clear(self):
        from src.dashboard import activity
        activity.clear_busy()
        assert activity.get_busy() is None

        activity.set_busy(0, "check my email please")
        busy = activity.get_busy()
        assert busy["channel"] == "dashboard"
        assert busy["preview"] == "check my email please"
        assert busy["since"]

        activity.set_busy(12345, "x" * 200)
        busy = activity.get_busy()
        assert busy["channel"] == "telegram"
        assert len(busy["preview"]) == 80

        activity.clear_busy()
        assert activity.get_busy() is None


class TestActivityParser:
    LOG = (
        "# Daily Log\n"
        "- [07:35] agent=kovo model=claude/sonnet\n"
        "User: Can you check your email\n"
        "Reply: Hey Esam! Unfortunately I don't have access yet.\n"
        "- [08:10] Reminder #3 fired: 'standup' (message)\n"
        "- [09:02] agent=kovo model=claude/opus\n"
        "User: call me with the weather\n"
        "Reply: Done — made the call.\n"
    )

    def test_parses_entries_newest_first(self):
        from src.dashboard.activity import parse_daily_log
        entries = parse_daily_log(self.LOG)
        assert len(entries) == 3
        assert entries[0]["time"] == "09:02"
        assert entries[-1]["time"] == "07:35"

    def test_chat_entries_prefer_user_message(self):
        from src.dashboard.activity import parse_daily_log
        entries = parse_daily_log(self.LOG)
        chat = entries[-1]
        assert chat["type"] == "chat"
        assert chat["text"].startswith("Can you check your email")
        assert chat["model"] == "claude/sonnet"

    def test_reminder_classified(self):
        from src.dashboard.activity import parse_daily_log
        entries = parse_daily_log(self.LOG)
        assert entries[1]["type"] == "reminder"

    def test_empty_log(self):
        from src.dashboard.activity import parse_daily_log
        assert parse_daily_log("") == []
        assert parse_daily_log(None) == []

    def test_limit(self):
        from src.dashboard.activity import parse_daily_log
        log = "".join(f"- [10:{i:02d}] note {i}\n" for i in range(40))
        assert len(parse_daily_log(log, limit=30)) == 30


class TestMetricsHistory:
    def test_add_prune_persist(self, tmp_path):
        from src.dashboard.metrics_history import MetricsHistory
        path = tmp_path / "hist.json"
        h = MetricsHistory(path=path)
        h.add_sample(cpu=1.0, ram=50.0, disk=60.0)
        assert len(h.samples()) == 1
        assert path.exists()

        # Reload from disk
        h2 = MetricsHistory(path=path)
        assert len(h2.samples()) == 1
        assert h2.samples()[0]["ram"] == 50.0

        # Samples older than the window get pruned
        h2._samples[0]["t"] = int(time.time()) - 25 * 3600
        assert h2.samples() == []

    def test_corrupt_file_recovers(self, tmp_path):
        from src.dashboard.metrics_history import MetricsHistory
        path = tmp_path / "hist.json"
        path.write_text("{not json")
        h = MetricsHistory(path=path)
        assert h.samples() == []


class TestMcpProbe:
    """The v2.1 lightweight probe — stdio path is testable without network."""

    def _probe(self, monkeypatch, entry):
        import asyncio
        from src.gateway import config as cfg
        from src.dashboard.routers.mcp import test_mcp_server
        monkeypatch.setattr(cfg, "get", lambda: {"mcp": {"srv": entry}})
        return asyncio.run(test_mcp_server("srv"))

    def test_stdio_command_found(self, monkeypatch):
        res = self._probe(monkeypatch, {"type": "stdio", "command": "echo"})
        assert res["reachable"] is True

    def test_stdio_command_missing(self, monkeypatch):
        res = self._probe(monkeypatch, {"type": "stdio", "command": "no-such-cmd-xyz"})
        assert res["reachable"] is False
        assert "not found" in res["error"]

    def test_unknown_server_404(self, monkeypatch):
        import asyncio
        import pytest as _pytest
        from fastapi import HTTPException
        from src.gateway import config as cfg
        from src.dashboard.routers.mcp import test_mcp_server
        monkeypatch.setattr(cfg, "get", lambda: {"mcp": {}})
        with _pytest.raises(HTTPException):
            asyncio.run(test_mcp_server("ghost"))


class TestReminderDashboardHelpers:
    @pytest.fixture
    def mgr(self, tmp_path):
        from src.tools.reminders import ReminderManager
        return ReminderManager(db_path=tmp_path / "test.db")

    def test_list_all_pending_spans_users(self, mgr):
        mgr.create(1, "owner reminder", "2199-01-01T10:00")
        mgr.create(0, "dashboard reminder", "2199-01-02T10:00")
        pending = mgr.list_all_pending()
        assert len(pending) == 2
        assert pending[0]["message"] == "owner reminder"  # sorted by due_at

    def test_cancel_any(self, mgr):
        rid = mgr.create(1, "to cancel", "2199-01-01T10:00")
        assert mgr.cancel_any(rid) is True
        assert mgr.list_all_pending() == []
        assert mgr.cancel_any(rid) is False  # already cancelled
        assert mgr.cancel_any(9999) is False
