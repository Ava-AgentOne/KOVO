"""
Streaming plumbing tests (Phase 3b) — no real Claude or Telegram calls.
Run: cd $KOVO_DIR && venv/bin/python -m pytest tests/ -v
"""
import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class TestRouterStreaming:
    @pytest.fixture(autouse=True)
    def _stub_config(self, monkeypatch):
        """Stub claude_timeout so tests don't need a deployed settings.yaml
        (a fresh clone ships only settings.yaml.template)."""
        from src.router import model_router
        monkeypatch.setattr(model_router.cfg, "claude_timeout", lambda: 300)

    def _router(self):
        from src.router.classifier import MessageClassifier
        from src.router.model_router import ModelRouter
        return ModelRouter(MessageClassifier())

    def test_streams_via_brain(self, monkeypatch):
        """on_delta + streaming brain -> brain.generate_stream is used."""
        import src.brains as brains
        from src.router import model_router

        fake = MagicMock()
        fake.supports_streaming = True
        fake.generate_stream = AsyncMock(
            return_value={"result": "STREAMED", "session_id": "s9"}
        )
        monkeypatch.setattr(brains, "get_claude_brain", lambda: fake)

        deltas = []

        async def on_delta(text):
            deltas.append(text)

        result = asyncio.run(
            self._router().route("hello there", on_delta=on_delta)
        )
        assert result["text"] == "STREAMED"
        assert result["session_id"] == "s9"
        fake.generate_stream.assert_awaited_once()
        assert fake.generate_stream.call_args.kwargs["on_delta"] is on_delta

    def test_no_streaming_brain_falls_back(self, monkeypatch):
        """on_delta given but CLI brain active -> classic call_claude path."""
        import src.brains as brains
        from src.router import model_router

        monkeypatch.setattr(brains, "get_claude_brain", lambda: None)
        monkeypatch.setattr(
            model_router, "call_claude",
            lambda *a, **k: {"result": "CLASSIC", "session_id": "s1"},
        )

        async def on_delta(text):
            pass

        result = asyncio.run(self._router().route("hello", on_delta=on_delta))
        assert result["text"] == "CLASSIC"

    def test_no_on_delta_never_touches_brain_stream(self, monkeypatch):
        import src.brains as brains
        from src.router import model_router

        fake = MagicMock()
        fake.supports_streaming = True
        fake.generate_stream = AsyncMock()
        monkeypatch.setattr(brains, "get_claude_brain", lambda: fake)
        monkeypatch.setattr(
            model_router, "call_claude",
            lambda *a, **k: {"result": "OK", "session_id": None},
        )

        result = asyncio.run(self._router().route("hello"))
        assert result["text"] == "OK"
        fake.generate_stream.assert_not_awaited()


class TestStreamingReply:
    def _msg(self):
        msg = MagicMock()
        placeholder = MagicMock()
        placeholder.edit_text = AsyncMock()
        placeholder.delete = AsyncMock()
        msg.reply_text = AsyncMock(return_value=placeholder)
        return msg, placeholder

    def test_placeholder_created_then_edited(self):
        from src.telegram.streaming import StreamingReply
        msg, placeholder = self._msg()
        s = StreamingReply(msg, interval=0)  # no throttle in tests

        asyncio.run(s.on_delta("Hello"))
        msg.reply_text.assert_awaited_once()
        assert "Hello" in msg.reply_text.call_args.args[0]

        asyncio.run(s.on_delta("Hello world"))
        placeholder.edit_text.assert_awaited_once()
        assert "Hello world" in placeholder.edit_text.call_args.args[0]
        assert s.streamed

    def test_throttle_skips_rapid_edits(self):
        from src.telegram.streaming import StreamingReply
        msg, placeholder = self._msg()
        s = StreamingReply(msg, interval=999)

        asyncio.run(s.on_delta("a"))
        asyncio.run(s.on_delta("ab"))
        asyncio.run(s.on_delta("abc"))
        # Only the first delta gets through the interval gate... which
        # creates the placeholder; later ones are throttled away.
        msg.reply_text.assert_awaited_once()
        placeholder.edit_text.assert_not_awaited()

    def test_finalize_edits_placeholder_with_markdown(self):
        from src.telegram.streaming import StreamingReply
        msg, placeholder = self._msg()
        s = StreamingReply(msg, interval=0)
        asyncio.run(s.on_delta("partial"))

        reply_fn = AsyncMock()
        asyncio.run(s.finalize("final text", reply_markup=None, reply_fn=reply_fn))
        # Placeholder edited with the final text (Markdown attempt first)
        args, kwargs = placeholder.edit_text.await_args_list[-1]
        assert args[0] == "final text"
        assert kwargs.get("parse_mode") == "Markdown"
        reply_fn.assert_not_awaited()  # single chunk fits in the placeholder

    def test_finalize_without_stream_uses_reply_fn(self):
        from src.telegram.streaming import StreamingReply
        msg, _ = self._msg()
        s = StreamingReply(msg, interval=0)  # no deltas ever

        reply_fn = AsyncMock()
        asyncio.run(s.finalize("plain reply", reply_markup="MARKUP", reply_fn=reply_fn))
        reply_fn.assert_awaited_once()
        args, kwargs = reply_fn.await_args
        assert args[1] == "plain reply"
        assert kwargs["reply_markup"] == "MARKUP"

    def test_finalize_chunks_long_text(self):
        from src.telegram.streaming import StreamingReply
        msg, _ = self._msg()
        s = StreamingReply(msg, interval=0)

        reply_fn = AsyncMock()
        long_text = "x" * 5000
        asyncio.run(s.finalize(long_text, reply_markup="KB", reply_fn=reply_fn))
        assert reply_fn.await_count == 2
        # markup only on the last chunk
        assert reply_fn.await_args_list[0].kwargs["reply_markup"] is None
        assert reply_fn.await_args_list[1].kwargs["reply_markup"] == "KB"

    def test_discard_deletes_placeholder(self):
        from src.telegram.streaming import StreamingReply
        msg, placeholder = self._msg()
        s = StreamingReply(msg, interval=0)
        asyncio.run(s.on_delta("partial"))
        asyncio.run(s.discard())
        placeholder.delete.assert_awaited_once()
        assert not s.streamed
