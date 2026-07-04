"""
Brain factory + dispatch tests — no real Claude calls.
Run: cd $KOVO_DIR && venv/bin/python -m pytest tests/ -v
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import src.brains as brains


@pytest.fixture(autouse=True)
def reset_brain_cache():
    brains._sdk_brain = None
    yield
    brains._sdk_brain = None


class TestBrainFactory:
    def test_default_is_cli(self, monkeypatch):
        """No brains config -> CLI path (factory returns None)."""
        from src.gateway import config as cfg
        monkeypatch.setattr(cfg, "get", lambda: {})
        assert brains.claude_backend() == "cli"
        assert brains.get_claude_brain() is None

    def test_sdk_selected(self, monkeypatch):
        from src.gateway import config as cfg
        monkeypatch.setattr(cfg, "get", lambda: {"brains": {"claude": "sdk"}})
        brain = brains.get_claude_brain()
        assert brain is not None
        assert brain.name == "claude-sdk"

    def test_explicit_cli(self, monkeypatch):
        from src.gateway import config as cfg
        monkeypatch.setattr(cfg, "get", lambda: {"brains": {"claude": "cli"}})
        assert brains.get_claude_brain() is None

    def test_config_error_falls_back_to_cli(self, monkeypatch):
        from src.gateway import config as cfg
        def boom():
            raise RuntimeError("no settings")
        monkeypatch.setattr(cfg, "get", boom)
        assert brains.claude_backend() == "cli"
        assert brains.get_claude_brain() is None


class TestCallClaudeDispatch:
    def test_dispatches_to_active_brain(self, monkeypatch):
        """call_claude() must route to the brain and never spawn a subprocess."""
        from src.tools import claude_cli

        fake = MagicMock()
        fake.generate.return_value = {"result": "BRAIN_OK", "session_id": "s1"}
        monkeypatch.setattr(brains, "get_claude_brain", lambda: fake)

        out = claude_cli.call_claude("hello", model="sonnet", timeout=5)
        assert out == {"result": "BRAIN_OK", "session_id": "s1"}
        fake.generate.assert_called_once()
        kwargs = fake.generate.call_args.kwargs
        assert kwargs["model"] == "sonnet"
        assert kwargs["timeout"] == 5

    def test_none_brain_means_cli_path(self, monkeypatch):
        """Factory returning None -> original subprocess path is used."""
        from src.tools import claude_cli

        monkeypatch.setattr(brains, "get_claude_brain", lambda: None)
        called = {}

        def fake_run(cmd, **kw):
            called["cmd"] = cmd
            m = MagicMock()
            m.returncode = 0
            m.stdout = '{"result": "CLI_PATH", "session_id": "s2"}'
            m.stderr = ""
            return m

        monkeypatch.setattr(claude_cli.subprocess, "run", fake_run)
        out = claude_cli.call_claude("hello")
        assert out["result"] == "CLI_PATH"
        assert called["cmd"][0] == "claude"


class TestSDKBrainShape:
    def test_permission_sentinel_shape(self):
        from src.brains.claude_sdk import ClaudeAgentSDKBrain
        s = ClaudeAgentSDKBrain._permission_sentinel("Bash(docker *)", "txt", "sid")
        assert s["__permission_needed__"] is True
        assert s["blocked_command"] == "docker"
        assert s["session_id"] == "sid"
