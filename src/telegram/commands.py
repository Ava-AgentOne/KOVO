"""
Telegram slash commands.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from telegram import Update
from telegram.ext import CallbackContext, ContextTypes

from src.telegram.formatting import (
    MAIN_KEYBOARD,
    agent_inline,
    format_agents,
    format_permissions,
    format_purge_review,
    format_skills,
    format_status,
    format_tools,
    perm_inline,
    purge_inline,
)

_DUBAI_TZ = timezone(timedelta(hours=4))


def _dubai_today():
    return datetime.now(_DUBAI_TZ).date()

log = logging.getLogger(__name__)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Kovo online. 🦞\n\n"
        "*Core*\n"
        "/status — system status\n"
        "/health — live health check\n"
        "/tools — tool registry\n"
        "/agents — sub-agents\n"
        "/model — force model (sonnet/opus)\n"
        "/clear — clear session\n\n"
        "*Memory & Skills*\n"
        "/memory — today's log\n"
        "/memory extracted — last extracted memories\n"
        "/memory search <query> — search memories\n"
        "/memory stats — memory statistics\n"
        "/flush — extract & save to MEMORY.md\n"
        "/skills — loaded skills\n"
        "/newskill — create skill\n\n"
        "*Database*\n"
        "/db — show DB schema\n"
        "/db query <question> — natural language query\n\n"
        "*Storage*\n"
        "/storage — disk usage report\n"
        "/purge <all|photos|documents|images> — clean old files\n\n"
        "*Phone*\n"
        "/call <text> — voice call or voice msg\n"
        "/reauth\\_caller — re-auth caller account\n\n"
        "*Permissions*\n"
        "/permissions — view sandbox allowlist\n"
        "/approve — grant pending permission\n"
        "/deny — reject pending permission\n\n"
        "*Other*\n"
        "/search <query> — web search\n"
        "/auth\\_google — Google OAuth setup\n"
        "/auth\\_github — GitHub token check\n\n"
        "_Tip: use the quick-access keyboard buttons below for common commands._",
        parse_mode="Markdown",
        reply_markup=MAIN_KEYBOARD,
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ollama = context.bot_data.get("ollama")
    ollama_ok = await ollama.is_available() if ollama else False

    tool_registry = context.bot_data.get("tool_registry")
    tools_ok    = sum(1 for t in tool_registry.available()) if tool_registry else 0
    tools_total = len(tool_registry.all()) if tool_registry else 0

    agent = context.bot_data.get("agent")
    sub_agents = agent.sub_agent_runner.all() if (agent and agent.sub_agent_runner) else []

    skills = context.bot_data.get("skills")
    skill_count = len(skills.all()) if skills else 0

    heartbeat = context.bot_data.get("heartbeat")
    hb_running = bool(heartbeat and heartbeat._started)

    text = format_status(
        ollama_ok=ollama_ok,
        hb_running=hb_running,
        tools_ok=tools_ok,
        tools_total=tools_total,
        sub_agent_count=len(sub_agents),
        skill_count=skill_count,
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=MAIN_KEYBOARD)


async def cmd_tools(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show tool registry with install/config status."""
    tool_registry = context.bot_data.get("tool_registry")
    if not tool_registry:
        await update.message.reply_text("Tool registry not available.")
        return
    text = format_tools(tool_registry.all())
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=MAIN_KEYBOARD)


async def cmd_agents(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show sub-agents."""
    agent = context.bot_data.get("agent")
    sub_agents = agent.sub_agent_runner.all() if (agent and agent.sub_agent_runner) else []
    text = format_agents(sub_agents)
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=MAIN_KEYBOARD)


async def cmd_skills(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    skills = context.bot_data.get("skills")
    text = format_skills(skills.all() if skills else [])
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=MAIN_KEYBOARD)


async def cmd_health(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Run a live health check and report results with progress bars."""
    await update.message.chat.send_action("typing")

    def _get_health():
        from src.heartbeat.checks import gather_quick_health, check_thresholds
        from src.telegram.formatting import format_health
        health_raw = gather_quick_health()
        alerts = check_thresholds(health_raw)
        return format_health(alerts)

    loop = asyncio.get_event_loop()
    text = await loop.run_in_executor(None, _get_health)
    if len(text) > 4096:
        text = text[:4090] + "…"
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=MAIN_KEYBOARD)


async def cmd_model(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []
    valid = {"sonnet", "opus", "clear"}
    if not args or args[0] not in valid:
        await update.message.reply_text(
            "Usage: `/model <sonnet|opus|clear>`\n"
            "Sets the model for your next message only.\n"
            "By default, complex tasks (code, debugging, design, planning) auto-escalate to Opus.",
            parse_mode="Markdown",
        )
        return
    if args[0] == "clear":
        context.user_data.pop("force_model", None)
        await update.message.reply_text("Model override cleared.")
    else:
        context.user_data["force_model"] = args[0]
        await update.message.reply_text(f"Next message will use: *{args[0]}*", parse_mode="Markdown")


async def cmd_memory(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []
    subcommand = args[0].lower() if args else ""

    memory = context.bot_data.get("memory")
    store = context.bot_data.get("structured_store")

    if not memory:
        await update.message.reply_text("Memory manager not available.")
        return

    # ── /memory extracted ─────────────────────────────────────────────────
    if subcommand == "extracted":
        if not store:
            await update.message.reply_text("Structured store not available.")
            return
        rows = store.execute(
            "SELECT content, category, created_at FROM memories "
            "ORDER BY created_at DESC LIMIT 20"
        )
        if not rows:
            await update.message.reply_text("No extracted memories yet. Try /flush first.")
            return
        lines = [f"*Last {len(rows)} extracted memories:*\n"]
        for r in rows:
            lines.append(f"• `[{r['category']}]` {r['content']}")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        return

    # ── /memory search <query> ────────────────────────────────────────────
    if subcommand == "search":
        query = " ".join(args[1:]).strip()
        if not query:
            await update.message.reply_text("Usage: `/memory search <query>`", parse_mode="Markdown")
            return
        results = []
        if store:
            rows = store.execute(
                "SELECT content, category FROM memories WHERE lower(content) LIKE ? LIMIT 10",
                (f"%{query.lower()}%",),
            )
            results = [f"• `[{r['category']}]` {r['content']}" for r in rows]
        # Also grep MEMORY.md
        main_mem = memory.main_memory()
        for line in main_mem.splitlines():
            if query.lower() in line.lower() and line.strip():
                results.append(f"• {line.strip()}")
        if not results:
            await update.message.reply_text(f"No memories matching: `{query}`", parse_mode="Markdown")
            return
        seen = list(dict.fromkeys(results))[:15]
        await update.message.reply_text(
            f"*Memory search: {query}*\n\n" + "\n".join(seen),
            parse_mode="Markdown",
        )
        return

    # ── /memory stats ─────────────────────────────────────────────────────
    if subcommand == "stats":
        if not store:
            await update.message.reply_text("Structured store not available.")
            return
        stats = store.get_memory_stats()
        if "error" in stats:
            await update.message.reply_text(f"❌ {stats['error']}")
            return
        by_src = "\n".join(f"  • {k}: {v}" for k, v in stats["by_source"].items())
        by_cat = "\n".join(f"  • {k}: {v}" for k, v in stats["top_categories"].items())
        await update.message.reply_text(
            f"*Memory Statistics*\n\n"
            f"Total memories: *{stats['total']}*\n\n"
            f"By source:\n{by_src}\n\n"
            f"Top categories:\n{by_cat}",
            parse_mode="Markdown",
        )
        return

    # ── /memory (default) — today's log formatted as activity list ────────
    from src.telegram.formatting import format_memory_log
    today_log = memory.daily_log()
    if today_log:
        text = format_memory_log(today_log, _dubai_today())
    else:
        text = "🧠 No entries in today's log yet."
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=MAIN_KEYBOARD)


async def cmd_flush(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Flush today's session log to MEMORY.md — uses auto-extractor if available."""
    memory = context.bot_data.get("memory")
    if not memory:
        await update.message.reply_text("Memory not available.")
        return

    args = context.args or []

    # If user supplied text directly, store it immediately
    if args:
        learnings = " ".join(args)
        memory.flush_to_memory(learnings)
        await update.message.reply_text(
            f"✅ Saved to MEMORY.md:\n```\n{learnings[:800]}\n```",
            parse_mode="Markdown",
        )
        return

    # Use auto-extractor (Claude Sonnet, deduplication, SQLite + MEMORY.md)
    auto_extractor = context.bot_data.get("auto_extractor")
    if auto_extractor:
        await update.message.chat.send_action("typing")
        try:
            result = await auto_extractor.extract_and_store(force=True)
            await update.message.reply_text(f"✅ {result}", parse_mode="Markdown")
        except Exception as e:
            log.error("cmd_flush auto-extract failed: %s", e)
            await update.message.reply_text(f"❌ Extraction failed: {e}")
        return

    # Fallback: no extractor, just save last 500 chars of today's log
    today_log = memory.daily_log()
    if not today_log:
        await update.message.reply_text("Nothing to flush — today's log is empty.")
        return
    learnings = today_log[-500:]
    memory.flush_to_memory(learnings)
    await update.message.reply_text(
        f"✅ Saved to MEMORY.md:\n```\n{learnings[:800]}\n```",
        parse_mode="Markdown",
    )


async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clear this user's Claude session history (start fresh)."""
    agent = context.bot_data.get("agent")
    user_id = update.effective_user.id
    if agent:
        agent.clear_session(user_id)
        await update.message.reply_text("Session cleared. Starting fresh.")
    else:
        await update.message.reply_text("Agent not available.")


async def cmd_newskill(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Create a new skill interactively.
    Usage: /newskill <name> | <description> | <trigger1,trigger2> | <body>
    All parts separated by |
    """
    args_str = " ".join(context.args or [])
    parts = [p.strip() for p in args_str.split("|")]

    if len(parts) < 4:
        await update.message.reply_text(
            "Usage: `/newskill name | description | trigger1,trigger2 | skill body text`\n\n"
            "Example:\n"
            "`/newskill backup | Manage workspace backups | backup,archive,save | "
            "# Backup Skill\\nRun scripts/backup.sh to create workspace backup.`",
            parse_mode="Markdown",
        )
        return

    name, description, triggers_raw, body = parts[0], parts[1], parts[2], parts[3]
    triggers = [t.strip() for t in triggers_raw.split(",") if t.strip()]

    creator = context.bot_data.get("creator")
    if not creator:
        await update.message.reply_text("Skill creator not available.")
        return

    try:
        skill = creator.create(
            name=name,
            description=description,
            tools=[],
            triggers=triggers,
            body=body,
        )
        await update.message.reply_text(
            f"✅ Skill *{skill.name}* created\n"
            f"Triggers: `{', '.join(skill.triggers)}`",
            parse_mode="Markdown",
        )
    except Exception as e:
        log.error("Skill creation failed: %s", e)
        await update.message.reply_text(f"❌ Failed: {e}")


# ── Phase 7: Voice Calls ──────────────────────────────────────────────────────

async def cmd_call(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /call <message text>
    Places a Telegram voice call (or voice message fallback) with TTS audio.
    """
    text = " ".join(context.args or [])
    if not text:
        await update.message.reply_text(
            "Usage: `/call <message to speak>`\n"
            "Example: `/call Hey the owner, the disk is almost full!`",
            parse_mode="Markdown",
        )
        return

    agent = context.bot_data.get("agent")
    if not agent:
        await update.message.reply_text("Agent not available.")
        return

    await update.message.reply_text("📞 Placing call…")
    result = await agent.make_call(text, urgent=False)
    await update.message.reply_text(result.get("text", "Done."))


# ── Phase 6: Google ───────────────────────────────────────────────────────────

async def cmd_auth_google(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /auth_google — Step 1: generate the OAuth URL and wait for the user to paste the code.
    The user visits the URL, authorises, copies the code, and replies with it.
    Step 2 (code interception) is handled in bot._handle_message via google_auth_state.
    """
    # Cancel any in-progress auth for this user
    existing = context.user_data.pop("google_auth_state", None)
    if existing:
        log.debug("Cancelled previous google_auth_state for user %s", update.effective_user.id)

    try:
        from src.tools.google_api import start_auth_flow
        loop = asyncio.get_event_loop()
        auth_url, flow = await loop.run_in_executor(None, start_auth_flow)
    except Exception as e:
        await update.message.reply_text(f"❌ Auth setup failed: {e}")
        return

    context.user_data["google_auth_state"] = {"flow": flow}

    await update.message.reply_text(
        "🔐 *Google OAuth — Step 1 of 2*\n\n"
        "1\\. Open this URL in your browser:\n"
        f"`{auth_url}`\n\n"
        "2\\. Sign in and approve access\\.\n\n"
        "3\\. Copy the code shown and *reply here with just the code*\\.",
        parse_mode="MarkdownV2",
    )


# ── GitHub auth ───────────────────────────────────────────────────────────────

async def cmd_auth_github(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /auth_github — verify the GITHUB_TOKEN is valid and show the authenticated user.
    """
    try:
        from src.tools.github_api import GitHubTool, GitHubNotConfiguredError, GitHubError
        loop = asyncio.get_event_loop()
        tool = GitHubTool()
        user = await loop.run_in_executor(None, tool.get_authenticated_user)
        tool_registry = context.bot_data.get("tool_registry")
        if tool_registry:
            tool_registry.update_tool("github", status="configured", config_needed=None)
        await update.message.reply_text(
            f"✅ *GitHub authenticated*\n"
            f"• User: `{user['login']}`\n"
            f"• Name: {user['name'] or '—'}\n"
            f"• Public repos: {user['public_repos']}\n"
            f"• Profile: {user['url']}",
            parse_mode="Markdown",
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ GitHub auth failed: {e}\n\n"
            "Make sure `GITHUB_TOKEN` is set in `config/.env`.",
        )


# ── Phase 7: Caller re-auth ───────────────────────────────────────────────────

async def cmd_reauth_caller(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /reauth_caller +971XXXXXXXXX — Step 1 of two-step OTP auth.

    Starts the Pyrogram auth flow in the background (which sends the SMS),
    then asks the user to reply with the OTP code. The bot runs headless
    (no stdin), so the OTP must come via the next Telegram message.
    """
    args = context.args or []
    if not args:
        await update.message.reply_text(
            "Usage: `/reauth_caller +971XXXXXXXXX`\n"
            "Provide the phone number of the caller (userbot) account.",
            parse_mode="Markdown",
        )
        return

    phone = args[0]
    agent = context.bot_data.get("agent")
    caller = getattr(agent, "caller", None) if agent else None

    if not caller:
        await update.message.reply_text("❌ Caller not configured.")
        return

    # Cancel any existing in-progress reauth for this user
    existing = context.user_data.pop("reauth_state", None)
    if existing:
        existing["task"].cancel()

    # Create a Future that will be resolved when the user sends the OTP
    code_future: asyncio.Future = asyncio.get_event_loop().create_future()

    # Launch auth in the background — it will block internally on code_future
    task = asyncio.create_task(caller.start_reauth(phone, code_future))

    context.user_data["reauth_state"] = {
        "phone": phone,
        "code_future": code_future,
        "task": task,
    }

    await update.message.reply_text(
        f"📱 Sending OTP to `{phone}`…\n\n"
        "When the SMS arrives, *reply here with just the digits* — nothing else.\n"
        "_Waiting up to 5 minutes._",
        parse_mode="Markdown",
    )


# ── Phase 8: Browser / Search ─────────────────────────────────────────────────

async def cmd_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /search <query> — quick web search via DuckDuckGo.
    """
    query = " ".join(context.args or [])
    if not query:
        await update.message.reply_text("Usage: `/search <query>`", parse_mode="Markdown")
        return

    await update.message.chat.send_action("typing")
    try:
        from src.tools.browser import web_search
        results = await web_search(query, max_results=5)
        if not results:
            await update.message.reply_text("No results found.")
            return
        lines = [f"🔍 *{query}*\n"]
        for r in results:
            lines.append(f"• [{r['title']}]({r['url']})\n  {r['snippet'][:120]}")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown", disable_web_page_preview=True)
    except Exception as e:
        log.error("Search failed: %s", e)
        await update.message.reply_text(f"Search failed: {e}")


# ── Permissions ───────────────────────────────────────────────────────────────

async def cmd_permissions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /permissions — show the current Claude Code sandbox allowlist.
    """
    from src.tools.claude_cli import get_permissions
    perms = get_permissions()

    pending = context.bot_data.get("pending_permission")
    body = format_permissions(perms, pending)

    if len(body) > 4096:
        body = body[:4090] + "…"

    markup = perm_inline() if pending else MAIN_KEYBOARD
    await update.message.reply_text(body, parse_mode="Markdown", reply_markup=markup)


# ── Storage ───────────────────────────────────────────────────────────────────

async def cmd_storage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /storage — show disk usage bar and per-directory breakdown.
    """
    storage = context.bot_data.get("storage")
    if not storage:
        await update.message.reply_text("Storage manager not available.")
        return

    await update.message.chat.send_action("typing")
    try:
        from src.telegram.formatting import format_storage
        loop = asyncio.get_event_loop()

        def _build():
            from datetime import datetime, timezone, timedelta
            _DUBAI_TZ = timezone(timedelta(hours=4))
            usage = storage.get_disk_usage()
            state = storage._load_state()
            last_purge = "never"
            if "last_auto_purge" in state:
                try:
                    last_dt = datetime.fromisoformat(state["last_auto_purge"])
                    delta   = datetime.now(tz=_DUBAI_TZ) - last_dt
                    hours   = int(delta.total_seconds() / 3600)
                    last_purge = f"{hours}h ago" if hours else "just now"
                except Exception:
                    pass
            return format_storage(usage, last_purge)

        text = await loop.run_in_executor(None, _build)
        if len(text) > 4096:
            text = text[:4090] + "…"
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=MAIN_KEYBOARD)
    except Exception as e:
        log.error("cmd_storage failed: %s", e)
        await update.message.reply_text(f"❌ Storage report failed: {e}")


async def cmd_db(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /db — show the SQLite schema
    /db query <question> — natural language SELECT query
    """
    store = context.bot_data.get("structured_store")
    if not store:
        await update.message.reply_text("Structured store not available.")
        return

    args = context.args or []
    subcommand = args[0].lower() if args else ""

    # ── /db query <question> ──────────────────────────────────────────────
    if subcommand == "query":
        question = " ".join(args[1:]).strip()
        if not question:
            await update.message.reply_text(
                "Usage: `/db query <natural language question>`\n"
                "Example: `/db query how many memories do I have by category`",
                parse_mode="Markdown",
            )
            return
        await update.message.chat.send_action("typing")
        try:
            result = store.natural_query(question)
            msg = f"*DB Query*\n_{question}_\n\n```\n{result[:3500]}\n```"
            await update.message.reply_text(msg, parse_mode="Markdown")
        except Exception as e:
            log.error("cmd_db query failed: %s", e)
            await update.message.reply_text(f"❌ Query failed: {e}")
        return

    # ── /db (schema) ──────────────────────────────────────────────────────
    schema = store.get_schema()
    await update.message.reply_text(
        f"*SQLite Schema*\n\n```\n{schema}\n```",
        parse_mode="Markdown",
    )


async def cmd_purge(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /purge <all|photos|documents|images|confirm>

    Scan for and delete tier-2 files (those that need user approval).
    A confirmation step is required before any files are deleted.
    """
    storage = context.bot_data.get("storage")
    if not storage:
        await update.message.reply_text("Storage manager not available.")
        return

    args = context.args or []
    target = args[0].lower() if args else ""

    _VALID_TARGETS = {"all", "photos", "documents", "images", "confirm"}
    if target not in _VALID_TARGETS:
        await update.message.reply_text(
            "Usage:\n"
            "`/purge all` — review all old files\n"
            "`/purge photos` — old photos only\n"
            "`/purge documents` — old documents only\n"
            "`/purge images` — old images only\n"
            "`/purge confirm` — execute after confirmation",
            parse_mode="Markdown",
        )
        return

    # ── Execute confirmed purge (text fallback for /purge confirm) ────────
    if target == "confirm":
        pending = context.bot_data.pop("pending_purge", None)
        if not pending:
            await update.message.reply_text(
                "No pending purge. Run `/purge all` first.", parse_mode="Markdown"
            )
            return
        await update.message.chat.send_action("typing")
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, storage.purge_files, pending["files"]
            )
            await update.message.reply_text(
                f"✅ *Purge complete*\n\n"
                f"Deleted {result['deleted']} files, freed {result['freed_mb']}MB.",
                parse_mode="Markdown",
                reply_markup=MAIN_KEYBOARD,
            )
        except Exception as e:
            log.error("cmd_purge confirm failed: %s", e)
            await update.message.reply_text(f"❌ Purge failed: {e}")
        return

    # ── Scan and build confirmation ───────────────────────────────────────
    await update.message.chat.send_action("typing")
    try:
        loop = asyncio.get_event_loop()
        purgeable = await loop.run_in_executor(None, storage.scan_purgeable)
    except Exception as e:
        log.error("cmd_purge scan failed: %s", e)
        await update.message.reply_text(f"❌ Scan failed: {e}")
        return

    # Filter to requested directories
    if target != "all":
        purgeable = {k: v for k, v in purgeable.items() if k == target}

    if not purgeable:
        label = "selected directories" if target == "all" else f"{target}/"
        await update.message.reply_text(
            f"✅ Nothing to purge in {label} (all files are within retention limits)."
        )
        return

    # Collect all file paths for the pending state
    all_files: list[str] = []
    total_mb = 0.0
    for info in purgeable.values():
        all_files.extend(info["files"])
        total_mb += info["total_mb"]

    context.bot_data["pending_purge"] = {"files": all_files, "total_mb": total_mb}

    review_text = format_purge_review(purgeable)
    await update.message.reply_text(
        review_text,
        parse_mode="Markdown",
        reply_markup=purge_inline(),
    )


# ── Inline keyboard callback handler ─────────────────────────────────────────

async def button_callback(update: Update, context: CallbackContext) -> None:
    """Handle all inline keyboard button presses."""
    query = update.callback_query
    await query.answer()
    data = query.data or ""

    # ── Permission approve ─────────────────────────────────────────────────
    if data == "perm_approve":
        pending = context.bot_data.get("pending_permission")
        if not pending:
            await query.edit_message_text("No pending permission request.")
            return
        pattern = pending["pattern"]
        from src.tools.claude_cli import add_permission
        if not add_permission(pattern):
            await query.edit_message_text(f"❌ Failed to add `{pattern}` — check logs.")
            return
        await query.edit_message_text(
            f"✅ Added `{pattern}` to permissions. Retrying…",
            parse_mode="Markdown",
        )
        context.bot_data.pop("pending_permission", None)
        agent = context.bot_data.get("agent")
        if not agent:
            return
        await query.message.chat.send_action("typing")
        result = await agent.handle(
            message=pending["message"],
            user_id=pending["user_id"],
            force_complexity=pending.get("force_complexity"),
        )
        if result.get("__permission_needed__"):
            pattern2   = result["pattern"]
            blocked2   = result.get("blocked_command", pattern2)
            context.bot_data["pending_permission"] = {
                "message":         pending["message"],
                "user_id":         pending["user_id"],
                "pattern":         pattern2,
                "blocked_command": blocked2,
                "force_complexity": pending.get("force_complexity"),
            }
            await query.message.reply_text(
                f"🔒 *Another permission needed*\n\n"
                f"Command: `{blocked2}`\nPattern: `{pattern2}`",
                parse_mode="Markdown",
                reply_markup=perm_inline(),
            )
            return
        resp = result.get("text", "(no response)")
        chunks = [resp[i : i + 4096] for i in range(0, max(len(resp), 1), 4096)]
        for i, chunk in enumerate(chunks):
            if chunk:
                markup = MAIN_KEYBOARD if i == len(chunks) - 1 else None
                await query.message.reply_text(chunk, reply_markup=markup)
        return

    # ── Permission deny ────────────────────────────────────────────────────
    if data == "perm_deny":
        pending = context.bot_data.pop("pending_permission", None)
        if not pending:
            await query.edit_message_text("No pending permission request.")
            return
        from src.tools.claude_cli import deny_permission
        deny_permission(pending.get("pattern", ""))
        await query.edit_message_text("❌ Permission denied. I'll find another way.")
        return

    # ── Purge confirm ──────────────────────────────────────────────────────
    if data == "purge_confirm":
        pending = context.bot_data.pop("pending_purge", None)
        if not pending:
            await query.edit_message_text("No pending purge. Run /purge first.")
            return
        storage = context.bot_data.get("storage")
        if not storage:
            await query.edit_message_text("Storage manager not available.")
            return
        await query.edit_message_text("⏳ Deleting files…")
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, storage.purge_files, pending["files"])
            await query.message.reply_text(
                f"✅ *Purge complete*\n\n"
                f"Deleted {result['deleted']} files, freed {result['freed_mb']}MB.",
                parse_mode="Markdown",
                reply_markup=MAIN_KEYBOARD,
            )
        except Exception as e:
            log.error("button_callback purge_confirm failed: %s", e)
            await query.message.reply_text(f"❌ Purge failed: {e}")
        return

    # ── Purge cancel ───────────────────────────────────────────────────────
    if data == "purge_cancel":
        context.bot_data.pop("pending_purge", None)
        await query.edit_message_text("Purge cancelled.")
        return

    # ── Sub-agent approve ──────────────────────────────────────────────────
    if data == "agent_approve":
        pending = context.bot_data.pop("pending_agent", None)
        if not pending:
            await query.edit_message_text("No pending sub-agent request.")
            return
        topic = pending.get("topic", "specialist")
        onboarding = context.bot_data.get("onboarding")
        if onboarding and hasattr(onboarding, "start_subagent"):
            onboarding.start_subagent(topic)
        await query.edit_message_text(
            f"✅ Starting *{topic}* agent setup…\n"
            f"Tell me what it should focus on.",
            parse_mode="Markdown",
        )
        return

    # ── Sub-agent deny ─────────────────────────────────────────────────────
    if data == "agent_deny":
        context.bot_data.pop("pending_agent", None)
        await query.edit_message_text("Skipped. I'll keep handling it directly.")
        return

    await query.answer("Unknown action.")
