"""
Native toolkit tests (Phase 3c) — no real calls, images, or reminders.
Run: cd $KOVO_DIR && venv/bin/python -m pytest tests/ -v
"""
import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.agents import toolkit


@pytest.fixture(autouse=True)
def clean_runtime():
    toolkit.RUNTIME.main_loop = None
    toolkit.RUNTIME.agent = None
    toolkit.RUNTIME.reminders = None
    toolkit.RUNTIME.tg_bot = None
    toolkit.RUNTIME.owner_chat_id = None
    toolkit._server = None
    yield
    toolkit.RUNTIME.main_loop = None
    toolkit.RUNTIME.agent = None
    toolkit.RUNTIME.reminders = None
    toolkit.RUNTIME.tg_bot = None
    toolkit.RUNTIME.owner_chat_id = None
    toolkit._server = None


def _wire(loop=None, **kw):
    defaults = dict(
        main_loop=loop,
        agent=MagicMock(),
        reminders=MagicMock(),
        tg_bot=MagicMock(),
        owner_chat_id=42,
    )
    defaults.update(kw)
    toolkit.set_runtime(**defaults)


class TestRuntime:
    def test_not_ready_means_no_mcp_config(self):
        assert toolkit.sdk_mcp_config() == {}

    def test_ready_after_wiring(self):
        async def run():
            _wire(loop=asyncio.get_running_loop())
            assert toolkit.RUNTIME.ready
            cfg = toolkit.sdk_mcp_config()
            assert "kovo" in cfg
        asyncio.run(run())

    def test_allowed_tool_names(self):
        names = toolkit.allowed_tool_names()
        assert "mcp__kovo__make_call" in names
        assert "mcp__kovo__send_image" in names
        assert "mcp__kovo__set_reminder" in names


class TestMakeCall:
    def test_calls_agent_and_reports_method(self):
        async def run():
            _wire(loop=asyncio.get_running_loop())
            toolkit.RUNTIME.agent.caller = object()
            toolkit.RUNTIME.agent.make_call = AsyncMock(
                return_value={"method": "call", "text": "📞 Delivered via call."}
            )
            out = await toolkit._make_call({"message": "weather report", "urgent": False})
            text = out["content"][0]["text"]
            assert "call" in text
            toolkit.RUNTIME.agent.make_call.assert_awaited_once_with("weather report", urgent=False)
        asyncio.run(run())

    def test_missing_caller_reports_unconfigured(self):
        async def run():
            _wire(loop=asyncio.get_running_loop())
            toolkit.RUNTIME.agent.caller = None
            out = await toolkit._make_call({"message": "hi"})
            assert "not configured" in out["content"][0]["text"]
        asyncio.run(run())

    def test_empty_message_rejected(self):
        async def run():
            _wire(loop=asyncio.get_running_loop())
            toolkit.RUNTIME.agent.caller = object()
            out = await toolkit._make_call({"message": ""})
            assert "required" in out["content"][0]["text"]
        asyncio.run(run())


class TestSetReminder:
    def test_creates_reminder(self):
        async def run():
            _wire(loop=asyncio.get_running_loop())
            toolkit.RUNTIME.reminders.create = MagicMock(return_value=7)
            out = await toolkit._set_reminder(
                {"message": "dentist", "due_at": "2026-07-03T15:00", "delivery": "both"}
            )
            assert "Reminder #7" in out["content"][0]["text"]
            toolkit.RUNTIME.reminders.create.assert_called_once_with(
                42, "dentist", "2026-07-03T15:00", "both"
            )
        asyncio.run(run())

    def test_invalid_delivery_defaults_to_message(self):
        async def run():
            _wire(loop=asyncio.get_running_loop())
            toolkit.RUNTIME.reminders.create = MagicMock(return_value=1)
            await toolkit._set_reminder(
                {"message": "x", "due_at": "2026-07-03T15:00", "delivery": "carrier-pigeon"}
            )
            assert toolkit.RUNTIME.reminders.create.call_args.args[3] == "message"
        asyncio.run(run())

    def test_bad_date_reports_format_hint(self):
        async def run():
            _wire(loop=asyncio.get_running_loop())
            toolkit.RUNTIME.reminders.create = MagicMock(side_effect=ValueError("bad"))
            out = await toolkit._set_reminder({"message": "x", "due_at": "tomorrowish"})
            assert "ISO format" in out["content"][0]["text"]
        asyncio.run(run())


class TestCrossLoopDispatch:
    def test_on_main_from_other_loop(self):
        """Tool handler on a private loop must execute on the main loop."""
        import threading

        results = {}
        main_loop_holder = {}

        async def main_side():
            main_loop_holder["loop"] = asyncio.get_running_loop()
            _wire(loop=main_loop_holder["loop"])
            toolkit.RUNTIME.agent.caller = object()

            async def record_call(message, urgent=False):
                results["loop"] = asyncio.get_running_loop()
                return {"method": "call", "text": "ok"}

            toolkit.RUNTIME.agent.make_call = record_call

            def worker():
                out = asyncio.run(toolkit._make_call({"message": "hi"}))
                results["out"] = out

            t = threading.Thread(target=worker)
            t.start()
            while t.is_alive():        # keep main loop serving callbacks
                await asyncio.sleep(0.01)
            t.join()

        asyncio.run(main_side())
        assert results["loop"] is main_loop_holder["loop"]
        assert "ok" in results["out"]["content"][0]["text"]
