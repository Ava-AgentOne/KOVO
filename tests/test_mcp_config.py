"""
External MCP config tests (Phase 3d) — no real servers contacted.
Run: cd $KOVO_DIR && venv/bin/python -m pytest tests/ -v
"""
import sys
from pathlib import Path

import pytest

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.agents import mcp_config


class TestSdkConfig:
    def test_sse_normalized(self):
        cfg = mcp_config._to_sdk_config("ha", {
            "type": "sse", "url": "http://x/sse",
            "headers": {"Authorization": "Bearer T"}, "enabled": True, "note": "x",
        })
        assert cfg == {"type": "sse", "url": "http://x/sse", "headers": {"Authorization": "Bearer T"}}
        # KOVO metadata (enabled, note) stripped
        assert "enabled" not in cfg and "note" not in cfg

    def test_http_normalized(self):
        cfg = mcp_config._to_sdk_config("gh", {"type": "http", "url": "https://x/mcp/"})
        assert cfg == {"type": "http", "url": "https://x/mcp/"}

    def test_stdio_infers_type_from_command(self):
        cfg = mcp_config._to_sdk_config("fs", {"command": "npx", "args": ["-y", "srv"]})
        assert cfg == {"type": "stdio", "command": "npx", "args": ["-y", "srv"]}

    def test_missing_url_rejected(self):
        assert mcp_config._to_sdk_config("bad", {"type": "sse"}) is None

    def test_missing_command_rejected(self):
        assert mcp_config._to_sdk_config("bad", {"type": "stdio"}) is None

    def test_no_type_no_command_rejected(self):
        assert mcp_config._to_sdk_config("bad", {"url": "http://x"}) is None


class TestExternalServers:
    def test_reads_and_filters_disabled(self, monkeypatch):
        from src.gateway import config as cfg
        monkeypatch.setattr(cfg, "get", lambda: {"mcp": {
            "ha": {"type": "sse", "url": "http://ha/sse"},
            "off": {"type": "http", "url": "http://off", "enabled": False},
        }})
        servers = mcp_config.external_servers()
        assert set(servers.keys()) == {"ha"}

    def test_empty_when_no_mcp(self, monkeypatch):
        from src.gateway import config as cfg
        monkeypatch.setattr(cfg, "get", lambda: {})
        assert mcp_config.external_servers() == {}

    def test_allowed_tools_prefix(self, monkeypatch):
        from src.gateway import config as cfg
        monkeypatch.setattr(cfg, "get", lambda: {"mcp": {
            "ha": {"type": "sse", "url": "http://ha/sse"},
            "gh": {"type": "http", "url": "http://gh"},
        }})
        tools = set(mcp_config.external_allowed_tools())
        assert tools == {"mcp__ha", "mcp__gh"}


class TestCrud:
    @pytest.fixture(autouse=True)
    def temp_settings(self, tmp_path, monkeypatch):
        f = tmp_path / "settings.yaml"
        f.write_text("kovo:\n  timezone: UTC\n")
        monkeypatch.setattr(mcp_config, "_SETTINGS_FILE", f)
        # Stub config.reload so _write_raw doesn't touch the real cache
        from src.gateway import config as cfg
        monkeypatch.setattr(cfg, "reload", lambda: None)
        yield f

    def test_add_and_list(self, temp_settings):
        mcp_config.add_server("ha", {"type": "sse", "url": "http://ha/sse", "enabled": True})
        servers = mcp_config.list_servers()
        assert len(servers) == 1
        assert servers[0]["name"] == "ha"
        assert servers[0]["type"] == "sse"
        assert servers[0]["enabled"] is True

    def test_add_rejects_bad_name(self):
        with pytest.raises(ValueError):
            mcp_config.add_server("bad name!", {"type": "sse", "url": "http://x"})

    def test_add_rejects_invalid_config(self):
        with pytest.raises(ValueError):
            mcp_config.add_server("ha", {"type": "sse"})  # no url

    def test_headers_masked_in_list(self, temp_settings):
        mcp_config.add_server("ha", {
            "type": "sse", "url": "http://ha/sse",
            "headers": {"Authorization": "Bearer supersecrettoken123", "X-Ref": "${HA_TOKEN}"},
        })
        h = mcp_config.list_servers()[0]["headers"]
        assert "supersecrettoken123" not in h["Authorization"]  # masked
        assert h["X-Ref"] == "${HA_TOKEN}"                       # placeholder preserved

    def test_placeholder_with_prefix_not_mangled(self, temp_settings):
        """v2.1 bug fix: 'Bearer ${HA_TOKEN}' used to display as 'Bear…N}'."""
        mcp_config.add_server("ha", {
            "type": "sse", "url": "http://ha/sse",
            "headers": {"Authorization": "Bearer ${HA_TOKEN}"},
        })
        h = mcp_config.list_servers()[0]["headers"]
        assert h["Authorization"] == "Bearer ${HA_TOKEN}"

    def test_toggle(self, temp_settings):
        mcp_config.add_server("ha", {"type": "sse", "url": "http://ha/sse"})
        assert mcp_config.set_enabled("ha", False) is True
        assert mcp_config.list_servers()[0]["enabled"] is False
        assert mcp_config.set_enabled("missing", True) is False

    def test_remove(self, temp_settings):
        mcp_config.add_server("ha", {"type": "sse", "url": "http://ha/sse"})
        assert mcp_config.remove_server("ha") is True
        assert mcp_config.list_servers() == []
        assert mcp_config.remove_server("ha") is False

    def test_write_preserves_other_config(self, temp_settings):
        mcp_config.add_server("ha", {"type": "sse", "url": "http://ha/sse"})
        import yaml
        data = yaml.safe_load(temp_settings.read_text())
        assert data["kovo"]["timezone"] == "UTC"   # untouched
        assert "ha" in data["mcp"]
