"""
Off-site backup tests (v3.0 Phase 0) — pure logic + config gating.
No network, no Google.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.tools import offsite_backup as osb


class TestSelectPrunable:
    def _files(self, n):
        return [{"id": str(i), "name": f"b{i}", "createdTime": f"2026-07-{i:02d}T04:00:00Z"}
                for i in range(1, n + 1)]

    def test_keeps_newest(self):
        files = self._files(10)
        doomed = osb.select_prunable(files, keep=7)
        assert len(doomed) == 3
        assert {f["id"] for f in doomed} == {"1", "2", "3"}  # oldest three

    def test_under_limit_prunes_nothing(self):
        assert osb.select_prunable(self._files(5), keep=7) == []
        assert osb.select_prunable([], keep=7) == []

    def test_missing_created_time_sorts_oldest(self):
        files = self._files(3) + [{"id": "x", "name": "no-ts"}]
        doomed = osb.select_prunable(files, keep=3)
        assert [f["id"] for f in doomed] == ["x"]


class TestEnabledGate:
    def test_disabled_by_config(self, monkeypatch):
        from src.gateway import config as cfg
        monkeypatch.setattr(cfg, "get", lambda: {"backup": {"offsite": {"enabled": False}}})
        assert osb.is_enabled() is False

    def test_enabled_requires_google_token(self, monkeypatch, tmp_path):
        from src.gateway import config as cfg
        monkeypatch.setattr(cfg, "get", lambda: {"backup": {"offsite": {"enabled": True}}})
        monkeypatch.setattr(osb, "kovo_dir", lambda: tmp_path)   # no token file
        assert osb.is_enabled() is False
        (tmp_path / "config").mkdir()
        (tmp_path / "config" / "google-token.json").write_text("{}")
        assert osb.is_enabled() is True

    def test_keep_count_parsing(self, monkeypatch):
        from src.gateway import config as cfg
        monkeypatch.setattr(cfg, "get", lambda: {"backup": {"offsite": {"keep": "3"}}})
        assert osb._keep_count() == 3
        monkeypatch.setattr(cfg, "get", lambda: {"backup": {"offsite": {"keep": "junk"}}})
        assert osb._keep_count() == 7
        monkeypatch.setattr(cfg, "get", lambda: {})
        assert osb._keep_count() == 7


class TestRunFailurePaths:
    def test_backup_script_failure_is_reported(self, monkeypatch):
        import subprocess
        from types import SimpleNamespace
        monkeypatch.setattr(subprocess, "run",
                            lambda *a, **k: SimpleNamespace(returncode=1, stderr="boom", stdout=""))
        result = osb.run_offsite_backup()
        assert result["ok"] is False
        assert "backup.sh failed" in result["error"]
