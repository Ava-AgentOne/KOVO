"""
KOVO native tools (Phase 3c) — real tool use via the Agent SDK.

Replaces the [MAKE_CALL] / [SEND_IMAGE] / [SET_REMINDER] text-tag hacks:
the SDK brain exposes an in-process MCP server so Claude invokes these as
first-class tools mid-conversation and receives the results back (e.g.
"call unanswered — delivered as voice message").

The gateway wires the runtime at startup via set_runtime(). Tool handlers
execute on the brain's event loop, which for non-streamed calls is NOT
the main loop — while telegram/pyrogram objects are loop-bound — so every
runtime interaction is dispatched through _on_main().

The old tag handlers in bot.py stay untouched as the fallback path for
the CLI brain (which has no tool support).
"""
from __future__ import annotations

import asyncio
import logging

log = logging.getLogger(__name__)


class _Runtime:
    main_loop: asyncio.AbstractEventLoop | None = None
    agent = None          # KovoAgent (make_call: tts + caller)
    reminders = None      # ReminderManager
    tg_bot = None         # telegram Bot (send_photo etc.)
    owner_chat_id: int | None = None

    @property
    def ready(self) -> bool:
        return self.main_loop is not None and self.agent is not None


RUNTIME = _Runtime()


def set_runtime(main_loop, agent, reminders=None, tg_bot=None, owner_chat_id=None) -> None:
    """Called once by the gateway after all deps exist."""
    RUNTIME.main_loop = main_loop
    RUNTIME.agent = agent
    RUNTIME.reminders = reminders
    RUNTIME.tg_bot = tg_bot
    RUNTIME.owner_chat_id = owner_chat_id
    log.info("Native toolkit runtime wired (chat_id=%s)", owner_chat_id)


async def _on_main(coro):
    """Await coro on the main event loop regardless of the calling loop."""
    loop = asyncio.get_running_loop()
    if RUNTIME.main_loop is None or RUNTIME.main_loop is loop:
        return await coro
    fut = asyncio.run_coroutine_threadsafe(coro, RUNTIME.main_loop)
    return await asyncio.wrap_future(fut)


def _text(msg: str) -> dict:
    return {"content": [{"type": "text", "text": msg}]}


# ── tool implementations ─────────────────────────────────────────────────────

async def _make_call(args: dict) -> dict:
    if RUNTIME.agent is None or RUNTIME.agent.caller is None:
        return _text("Phone tool not configured — tell the owner to check TOOLS.md.")
    message = str(args.get("message", "")).strip()
    if not message:
        return _text("Error: message is required.")
    urgent = bool(args.get("urgent", False))
    result = await _on_main(RUNTIME.agent.make_call(message, urgent=urgent))
    return _text(f"Delivered via {result.get('method', 'unknown')}: {result.get('text', '')}")


async def _send_image(args: dict) -> dict:
    query = str(args.get("query", "")).strip()
    if not query:
        return _text("Error: query is required.")
    if RUNTIME.tg_bot is None or RUNTIME.owner_chat_id is None:
        return _text("Telegram not available — cannot send images right now.")
    try:
        from src.tools.image import fetch_image
    except ImportError:
        return _text("Image tool not installed (ddgs missing).")

    async def _fetch_and_send():
        path = await fetch_image(query, filename="tg_image")
        if not path:
            return None
        with open(path, "rb") as fh:
            await RUNTIME.tg_bot.send_photo(
                chat_id=RUNTIME.owner_chat_id, photo=fh, caption=f"🔍 {query}",
                read_timeout=30, write_timeout=60, connect_timeout=15,
            )
        return path

    try:
        path = await _on_main(_fetch_and_send())
    except Exception as e:
        log.error("send_image tool failed: %s", e)
        return _text(f"Image send failed: {e}")
    if not path:
        return _text(f"No image found for: {query}")
    return _text(f"Image for '{query}' sent to the owner's chat.")


async def _set_reminder(args: dict) -> dict:
    if RUNTIME.reminders is None or RUNTIME.owner_chat_id is None:
        return _text("Reminder system not available.")
    message = str(args.get("message", "")).strip()
    due_at = str(args.get("due_at", "")).strip()
    delivery = str(args.get("delivery", "message")).strip().lower()
    if delivery not in ("message", "call", "both"):
        delivery = "message"
    if not message or not due_at:
        return _text("Error: message and due_at are both required.")

    async def _create():
        return RUNTIME.reminders.create(RUNTIME.owner_chat_id, message, due_at, delivery)

    try:
        rid = await _on_main(_create())
    except ValueError:
        return _text(f"Invalid due_at '{due_at}' — use ISO format like 2026-07-03T15:00.")
    except Exception as e:
        return _text(f"Reminder creation failed: {e}")
    return _text(f"Reminder #{rid} set for {due_at} (delivery: {delivery}).")


# ── SDK server assembly ──────────────────────────────────────────────────────

_TOOL_NAMES = ["make_call", "send_image", "set_reminder"]
_server = None


def sdk_mcp_config() -> dict:
    """mcp_servers dict for ClaudeAgentOptions — {} when runtime not wired."""
    global _server
    if not RUNTIME.ready:
        return {}
    if _server is None:
        try:
            from claude_agent_sdk import create_sdk_mcp_server, tool

            make_call = tool(
                "make_call",
                "Place a real voice call to the owner's phone via Telegram, speaking the "
                "given message aloud (TTS). Falls back to a voice message if unanswered. "
                "Use when the owner asks to be called or for urgent alerts.",
                {"message": str, "urgent": bool},
            )(_make_call)

            send_image = tool(
                "send_image",
                "Search the web for an image and send it to the owner's Telegram chat. "
                "Use whenever the owner asks to see a photo, picture, or visual.",
                {"query": str},
            )(_send_image)

            set_reminder = tool(
                "set_reminder",
                "Schedule a reminder for the owner. due_at is ISO local time like "
                "2026-07-03T15:00. delivery is one of: message, call, both.",
                {"message": str, "due_at": str, "delivery": str},
            )(_set_reminder)

            _server = create_sdk_mcp_server(
                name="kovo", version="1.0.0", tools=[make_call, send_image, set_reminder]
            )
        except Exception as e:
            log.error("SDK toolkit unavailable: %s", e)
            return {}
    return {"kovo": _server}


def allowed_tool_names() -> list[str]:
    return [f"mcp__kovo__{n}" for n in _TOOL_NAMES]


def system_prompt_block() -> str:
    """Replaces the tag-instruction blocks when the SDK brain is active."""
    return (
        "## Native Tools\n"
        "You have real tools you can invoke directly (no text tags needed):\n"
        "- make_call(message, urgent): place a real voice call to the owner's phone, "
        "speaking the message aloud. Falls back to a voice message if unanswered.\n"
        "- send_image(query): search for an image and send it to the owner's chat. "
        "Use whenever the owner asks to see a photo, picture, or visual.\n"
        "- set_reminder(message, due_at, delivery): schedule a reminder. due_at is ISO "
        "local time (e.g. 2026-07-03T15:00); delivery is message, call, or both.\n"
        "Call these tools when the owner asks to be called, shown an image, or reminded — "
        "do NOT write [MAKE_CALL:], [SEND_IMAGE:] or [SET_REMINDER:] text tags."
    )
