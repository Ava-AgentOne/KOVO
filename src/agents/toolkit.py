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
    routines = None       # RoutineManager (v3.0)
    transcriber = None    # Transcriber (v3.0 live calls)
    owner_chat_id: int | None = None

    @property
    def ready(self) -> bool:
        return self.main_loop is not None and self.agent is not None


RUNTIME = _Runtime()


def _owner_channel():
    """Owner's preferred channel from the registry (Phase 3e)."""
    from src.channels import registry
    return registry.owner_channel()


def set_runtime(main_loop, agent, reminders=None, owner_chat_id=None,
                routines=None, transcriber=None) -> None:
    """Called once by the gateway after all deps exist.

    Message/photo delivery goes through src.channels (registry) — the
    toolkit no longer holds a bot object directly.
    """
    RUNTIME.main_loop = main_loop
    RUNTIME.agent = agent
    RUNTIME.reminders = reminders
    RUNTIME.routines = routines
    RUNTIME.transcriber = transcriber
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
    from src.channels import PHOTOS
    channel = _owner_channel()
    if channel is None or RUNTIME.owner_chat_id is None:
        return _text("No chat channel available — cannot send images right now.")
    if not channel.can(PHOTOS):
        return _text(f"The {channel.name} channel cannot display photos.")
    try:
        from src.tools.image import fetch_image
    except ImportError:
        return _text("Image tool not installed (ddgs missing).")

    async def _fetch_and_send():
        path = await fetch_image(query, filename="tg_image")
        if not path:
            return None
        await channel.send_photo(RUNTIME.owner_chat_id, path, caption=f"🔍 {query}")
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


async def _set_routine(args: dict) -> dict:
    """Create a recurring autonomous task (v3.0). The model converts the
    owner's natural-language schedule to cron before calling this."""
    if RUNTIME.routines is None or RUNTIME.owner_chat_id is None:
        return _text("Routine system not available.")
    name = str(args.get("name", "")).strip()
    prompt = str(args.get("prompt", "")).strip()
    cron = str(args.get("cron", "")).strip()
    schedule_text = str(args.get("schedule_text", "")).strip()
    delivery = str(args.get("delivery", "message")).strip().lower()
    if delivery not in ("message", "silent"):
        delivery = "message"
    if not (name and prompt and cron):
        return _text("Error: name, prompt, and cron are all required.")
    try:
        rid = RUNTIME.routines.create(
            RUNTIME.owner_chat_id, name, prompt, cron,
            schedule_text=schedule_text, delivery=delivery,
        )
        nxt = RUNTIME.routines.get(rid)["next_run"]
    except ValueError as e:
        return _text(f"Could not create routine: {e}")
    except Exception as e:
        return _text(f"Routine creation failed: {e}")
    return _text(
        f"Routine #{rid} '{name}' created — {schedule_text or cron}, "
        f"next run {nxt}. The owner can manage it on the dashboard Routines page."
    )


async def _list_routines(args: dict) -> dict:
    if RUNTIME.routines is None:
        return _text("Routine system not available.")
    items = RUNTIME.routines.list_all()
    if not items:
        return _text("No routines exist yet.")
    lines = []
    for r in items:
        state = "on" if r["enabled"] else "OFF"
        lines.append(
            f"#{r['id']} [{state}] {r['name']} — {r['schedule_text'] or r['cron']}"
            f" (next: {r['next_run']}, last: {r['last_status'] or 'never'})"
        )
    return _text("\n".join(lines))


async def _cancel_routine(args: dict) -> dict:
    if RUNTIME.routines is None:
        return _text("Routine system not available.")
    ident = str(args.get("name_or_id", "")).strip()
    if not ident:
        return _text("Error: name_or_id is required.")
    r = (RUNTIME.routines.get(int(ident)) if ident.isdigit()
         else RUNTIME.routines.get_by_name(ident))
    if not r:
        return _text(f"No routine found matching {ident!r}.")
    RUNTIME.routines.delete(r["id"])
    return _text(f"Routine #{r['id']} '{r['name']}' deleted.")


async def _start_live_call(args: dict) -> dict:
    """Ring the owner for a live two-way voice conversation (v3.0 3c)."""
    from src.tools import live_call as lc
    if not lc.is_enabled():
        return _text("Live Call is experimental and disabled. The owner can "
                     "enable it via settings.yaml: experimental.live_call: true.")
    if RUNTIME.agent is None or RUNTIME.transcriber is None or RUNTIME.owner_chat_id is None:
        return _text("Live calls not available (agent/transcriber not wired).")
    if getattr(RUNTIME.agent, "tts", None) is None:
        return _text("Live calls need TTS configured.")
    if lc.is_active():
        return _text("A live call is already running.")
    import os
    from src.gateway import config as cfg
    call_cfg = cfg.get().get("telegram_call", {})
    try:
        session = lc.LiveCallSession(
            agent=RUNTIME.agent, transcriber=RUNTIME.transcriber,
            owner_id=RUNTIME.owner_chat_id,
            api_id=int(call_cfg.get("api_id") or os.environ["TELEGRAM_API_ID"]),
            api_hash=str(call_cfg.get("api_hash") or os.environ["TELEGRAM_API_HASH"]),
        )
    except KeyError:
        return _text("Live calls need telegram_call api_id/api_hash configured.")
    # Fire on the MAIN loop and return immediately — the call outlives this turn.
    asyncio.run_coroutine_threadsafe(session.run(), RUNTIME.main_loop)
    return _text("📞 Calling the owner now for a live conversation. "
                 "They can say goodbye to end it.")


# ── SDK server assembly ──────────────────────────────────────────────────────

_TOOL_NAMES = ["make_call", "send_image", "set_reminder",
               "set_routine", "list_routines", "cancel_routine",
               "start_live_call"]
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

            set_routine = tool(
                "set_routine",
                "Create a RECURRING autonomous task (routine): the prompt runs on a "
                "cron schedule and the result is sent to the owner. Convert the "
                "owner's natural-language schedule to a 5-field cron expression "
                "yourself (e.g. 'every weekday at 7am' -> '0 7 * * mon-fri'). "
                "schedule_text is the human-readable schedule. delivery: message "
                "(send result) or silent (history only).",
                {"name": str, "prompt": str, "cron": str,
                 "schedule_text": str, "delivery": str},
            )(_set_routine)

            list_routines = tool(
                "list_routines",
                "List the owner's routines with schedule, next run, and last status.",
                {},
            )(_list_routines)

            cancel_routine = tool(
                "cancel_routine",
                "Delete a routine by its name or numeric id.",
                {"name_or_id": str},
            )(_cancel_routine)

            start_live_call = tool(
                "start_live_call",
                "Ring the owner's phone for a LIVE two-way voice conversation — "
                "Kovo listens and answers in real time during the call. Use when "
                "the owner asks to talk, have a call, or discuss something by voice. "
                "For one-way spoken announcements use make_call instead.",
                {},
            )(_start_live_call)

            _server = create_sdk_mcp_server(
                name="kovo", version="1.0.0",
                tools=[make_call, send_image, set_reminder,
                       set_routine, list_routines, cancel_routine,
                       start_live_call],
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
        "- set_reminder(message, due_at, delivery): schedule a ONE-TIME reminder. due_at "
        "is ISO local time (e.g. 2026-07-03T15:00); delivery is message, call, or both.\n"
        "- set_routine(name, prompt, cron, schedule_text, delivery): create a RECURRING "
        "autonomous task — the prompt runs on the cron schedule and the result is sent "
        "to the owner. Convert natural language to 5-field cron yourself "
        "('every weekday at 7am' -> '0 7 * * mon-fri'); put the human phrasing in "
        "schedule_text. Use for anything the owner wants regularly: checking email, "
        "morning briefings, weekly summaries.\n"
        "- list_routines() / cancel_routine(name_or_id): inspect or remove routines.\n"
        "- start_live_call(): ring the owner for a LIVE two-way conversation — "
        "use when they want to talk by voice; make_call is only for one-way announcements.\n"
        "One-time ask -> set_reminder. Recurring ask ('every', 'daily', 'each week') -> "
        "set_routine. Call these tools when the owner asks to be called, shown an image, "
        "reminded, or wants something done regularly — do NOT write [MAKE_CALL:], "
        "[SEND_IMAGE:] or [SET_REMINDER:] text tags."
    )
