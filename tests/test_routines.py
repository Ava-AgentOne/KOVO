"""
Kovo Routines tests (v3.0 Phase 1) — manager CRUD, cron handling, due
selection, run recording. No agent, no scheduler, no network.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.tools.routines import RoutineManager, next_fire


@pytest.fixture
def mgr(tmp_path):
    return RoutineManager(db_path=tmp_path / "test.db")


class TestCron:
    def test_next_fire_valid(self):
        nxt = next_fire("0 7 * * mon-fri")
        assert len(nxt) == 16 and "T" in nxt   # ISO minute

    def test_next_fire_invalid_raises(self):
        with pytest.raises(ValueError):
            next_fire("not a cron")
        with pytest.raises(ValueError):
            next_fire("99 99 * * *")


class TestCrud:
    def test_create_and_list(self, mgr):
        rid = mgr.create(777, "morning brief", "Summarize my day", "0 7 * * *",
                         schedule_text="Every day at 07:00")
        r = mgr.get(rid)
        assert r["name"] == "morning brief"
        assert r["enabled"] == 1
        assert r["next_run"]                      # computed on create
        assert mgr.get_by_name("MORNING BRIEF")   # case-insensitive

    def test_duplicate_name_rejected(self, mgr):
        mgr.create(777, "x", "p", "0 7 * * *")
        with pytest.raises(ValueError):
            mgr.create(777, "x", "other", "0 8 * * *")

    def test_invalid_inputs_rejected(self, mgr):
        with pytest.raises(ValueError):
            mgr.create(777, "", "p", "0 7 * * *")
        with pytest.raises(ValueError):
            mgr.create(777, "n", "p", "bad cron")
        with pytest.raises(ValueError):
            mgr.create(777, "n", "p", "0 7 * * *", delivery="carrier-pigeon")

    def test_toggle_recomputes_next_run(self, mgr):
        rid = mgr.create(777, "x", "p", "0 7 * * *")
        assert mgr.set_enabled(rid, False) is True
        assert mgr.get(rid)["enabled"] == 0
        assert mgr.set_enabled(rid, True) is True
        r = mgr.get(rid)
        assert r["enabled"] == 1 and r["next_run"]
        assert mgr.set_enabled(9999, True) is False

    def test_delete(self, mgr):
        rid = mgr.create(777, "x", "p", "0 7 * * *")
        assert mgr.delete(rid) is True
        assert mgr.get(rid) is None
        assert mgr.delete(rid) is False


class TestExecutionSupport:
    def test_due_selection(self, mgr):
        rid = mgr.create(777, "x", "p", "0 7 * * *")
        # Not due at a timestamp before next_run
        assert mgr.due("2000-01-01T00:00") == []
        # Due once now >= next_run
        due = mgr.due("2199-01-01T00:00")
        assert [d["id"] for d in due] == [rid]
        # Disabled routines never come due
        mgr.set_enabled(rid, False)
        assert mgr.due("2199-01-01T00:00") == []

    def test_record_run_advances_and_prunes(self, mgr):
        rid = mgr.create(777, "x", "p", "0 7 * * *")
        before = mgr.get(rid)["next_run"]
        for i in range(25):
            mgr.record_run(rid, "ok", f"result {i}", 1.5)
        r = mgr.get(rid)
        assert r["last_status"] == "ok"
        assert r["last_result"] == "result 24"
        assert r["next_run"] >= before          # recomputed forward
        runs = mgr.runs(rid, limit=50)
        assert len(runs) == 20                  # pruned to RUNS_KEPT
        assert runs[0]["result"] == "result 24" # newest first

    def test_long_result_truncated(self, mgr):
        rid = mgr.create(777, "x", "p", "0 7 * * *")
        mgr.record_run(rid, "ok", "y" * 5000, 1.0)
        assert len(mgr.get(rid)["last_result"]) == 1000
