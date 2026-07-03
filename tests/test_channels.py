"""
Channel abstraction tests (Phase 3e) — no real Telegram/network calls.
Run: cd $KOVO_DIR && venv/bin/python -m pytest tests/ -v
"""
import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.channels.base import (
    CALLS,
    PHOTOS,
    Channel,
    ChannelCapabilityError,
    ChannelRegistry,
)


class _FakeChannel(Channel):
    name = "fake"
    capabilities = frozenset({PHOTOS})

    def __init__(self):
        self.sent = []

    async def send_text(self, chat_id, text, markdown=True):
        self.sent.append((chat_id, text))


class TestChannelBase:
    def test_capability_check(self):
        ch = _FakeChannel()
        assert ch.can(PHOTOS)
        assert not ch.can(CALLS)

    def test_unsupported_capability_raises(self):
        ch = _FakeChannel()
        with pytest.raises(ChannelCapabilityError):
            asyncio.run(ch.send_voice(1, "/tmp/x.mp3"))


class TestRegistry:
    def test_register_and_get(self):
        reg = ChannelRegistry()
        ch = _FakeChannel()
        reg.register(ch)
        assert reg.get("fake") is ch
        assert reg.all() == [ch]

    def test_owner_channel_prefers_config(self, monkeypatch):
        from src.gateway import config as cfg
        reg = ChannelRegistry()
        fake = _FakeChannel()
        tele = _FakeChannel()
        tele.name = "telegram"
        reg.register(fake)
        reg.register(tele)

        monkeypatch.setattr(cfg, "get", lambda: {"channels": {"default": "fake"}})
        assert reg.owner_channel() is fake

        monkeypatch.setattr(cfg, "get", lambda: {})
        assert reg.owner_channel() is tele  # falls back to telegram

    def test_owner_channel_last_resort_any(self, monkeypatch):
        from src.gateway import config as cfg
        monkeypatch.setattr(cfg, "get", lambda: {})
        reg = ChannelRegistry()
        only = _FakeChannel()
        reg.register(only)
        assert reg.owner_channel() is only

    def test_empty_registry_returns_none(self, monkeypatch):
        from src.gateway import config as cfg
        monkeypatch.setattr(cfg, "get", lambda: {})
        assert ChannelRegistry().owner_channel() is None


class TestTelegramChannelSend:
    def _channel(self):
        from src.channels.telegram import TelegramChannel
        ch = TelegramChannel.__new__(TelegramChannel)  # skip build_application
        ch.app = MagicMock()
        ch.app.bot.send_message = AsyncMock()
        ch.app.bot.send_photo = AsyncMock()
        return ch

    def test_send_text_chunks_at_4096(self):
        ch = self._channel()
        asyncio.run(ch.send_text(1, "x" * 5000))
        assert ch.app.bot.send_message.await_count == 2

    def test_markdown_falls_back_to_plain(self):
        from telegram.error import BadRequest
        ch = self._channel()
        ch.app.bot.send_message = AsyncMock(side_effect=[BadRequest("bad md"), None])
        asyncio.run(ch.send_text(1, "broken *markdown"))
        assert ch.app.bot.send_message.await_count == 2
        # second attempt has no parse_mode
        assert "parse_mode" not in ch.app.bot.send_message.await_args_list[1].kwargs

    def test_empty_text_is_noop(self):
        ch = self._channel()
        asyncio.run(ch.send_text(1, ""))
        ch.app.bot.send_message.assert_not_awaited()


class TestDashboardChannel:
    def test_broadcast_appends_history_and_pushes(self):
        from src.channels.dashboard import DashboardChannel
        from src.dashboard.routers import chat

        history_before = len(chat._chat_history)
        ws = MagicMock()
        ws.send_json = AsyncMock()
        chat._active_sockets.add(ws)
        try:
            asyncio.run(DashboardChannel().send_text(0, "alert text"))
        finally:
            chat._active_sockets.discard(ws)

        assert len(chat._chat_history) == history_before + 1
        assert chat._chat_history[-1]["content"] == "alert text"
        ws.send_json.assert_awaited_once()
        frame = ws.send_json.await_args.args[0]
        assert frame["type"] == "message" and frame["role"] == "assistant"
        chat._chat_history.pop()

    def test_dead_socket_is_pruned(self):
        from src.channels.dashboard import DashboardChannel
        from src.dashboard.routers import chat

        ws = MagicMock()
        ws.send_json = AsyncMock(side_effect=RuntimeError("gone"))
        chat._active_sockets.add(ws)
        asyncio.run(DashboardChannel().send_text(0, "hello"))
        assert ws not in chat._active_sockets
        chat._chat_history.pop()


class TestReporterViaChannel:
    def test_reporter_sends_through_channel(self):
        from src.heartbeat.reporter import HeartbeatReporter
        ch = _FakeChannel()
        rep = HeartbeatReporter(channel=ch, owner_user_id=99)
        asyncio.run(rep.send_alert("disk almost full"))
        assert ch.sent and ch.sent[0][0] == 99
        assert "disk almost full" in ch.sent[0][1]
