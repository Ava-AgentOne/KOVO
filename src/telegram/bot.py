"""
Telegram bot — receives messages, routes through Kovo (single main agent), replies.
"""
import asyncio
import logging
import re
import subprocess
from pathlib import Path

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from src.gateway import config as cfg
from src.telegram import commands as cmd
from src.telegram.formatting import MAIN_KEYBOARD, BUTTON_TO_COMMAND, agent_inline, perm_inline
from src.telegram.middleware import auth_middleware

log = logging.getLogger(__name__)


async def _handle_reauth_otp(
    update: Update, context: ContextTypes.DEFAULT_TYPE, code: str
) -> None:
    """Step 2 of /reauth_caller — feed the OTP to the waiting Pyrogram task."""
    state = context.user_data.pop("reauth_state")
    code_future: asyncio.Future = state["code_future"]
    task: asyncio.Task = state["task"]

    if code_future.done():
        await update.message.reply_text("⚠️ OTP already submitted.")
        return

    code_future.set_result(code.strip())
    await update.message.reply_text("⏳ Verifying OTP…")

    def _mark_caller_configured():
        tool_registry = context.bot_data.get("tool_registry")
        if tool_registry:
            tool_registry.update_tool("telegram_call", status="configured", config_needed=None)

    try:
        result = await asyncio.wait_for(asyncio.shield(task), timeout=30)
        await update.message.reply_text(result)
        if result.startswith("✅"):
            _mark_caller_configured()
    except asyncio.TimeoutError:
        await update.message.reply_text(
            "⏳ Still authenticating — Telegram is slow. You'll get a reply when it finishes."
        )
        # Let the task finish on its own and swallow the result
        async def _finish():
            try:
                msg = await task
                await update.message.reply_text(msg)
                if msg.startswith("✅"):
                    _mark_caller_configured()
            except Exception as e:
                await update.message.reply_text(f"❌ Auth failed: {e}")
        asyncio.create_task(_finish())
    except Exception as e:
        await update.message.reply_text(f"❌ Auth failed: {e}")


async def _handle_google_auth_code(
    update: Update, context: ContextTypes.DEFAULT_TYPE, code: str
) -> None:
    """Step 2 of /auth_google — exchange the user-pasted code for a token."""
    state = context.user_data.pop("google_auth_state")
    flow = state["flow"]

    await update.message.reply_text("⏳ Completing Google auth…")
    try:
        from src.tools.google_api import complete_auth_flow
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, complete_auth_flow, flow, code)
        await update.message.reply_text(result)
        if result.startswith("✅"):
            tool_registry = context.bot_data.get("tool_registry")
            if tool_registry:
                tool_registry.update_tool("google_api", status="configured", config_needed=None)
    except Exception as e:
        await update.message.reply_text(f"❌ Auth failed: {e}")


_IMAGE_TAG_RE = re.compile(r"\[SEND_IMAGE:\s*(.+?)\]", re.IGNORECASE)


async def _handle_image_tags(update: Update, response_text: str) -> str:
    """
    Parse [SEND_IMAGE: query] tags from agent response.
    For each tag: fetch + send photo to the chat.
    Returns the cleaned response text (tags removed).
    """
    tags = _IMAGE_TAG_RE.findall(response_text)
    if not tags:
        return response_text

    try:
        from src.tools.image import fetch_image
    except ImportError:
        log.warning("image tool not available — duckduckgo-search may need installing")
        return _IMAGE_TAG_RE.sub("", response_text).strip()

    for query in tags:
        query = query.strip()
        log.info("image request: query=%r", query)
        await update.message.chat.send_action(ChatAction.UPLOAD_PHOTO)
        try:
            path = await fetch_image(query, filename="tg_image")
            if path:
                await update.message.reply_photo(
                    photo=open(path, "rb"),
                    caption=f"🔍 {query}",
                )
            else:
                await update.message.reply_text(f"⚠️ Couldn't find an image for: _{query}_", parse_mode="Markdown")
        except Exception as e:
            log.error("image send failed: %s", e)
            await update.message.reply_text(f"⚠️ Image failed: {e}")

    # Strip all tags from the text response
    return _IMAGE_TAG_RE.sub("", response_text).strip()


def _ffmpeg(args: list[str]) -> None:
    """Run an ffmpeg command, raise RuntimeError on failure."""
    proc = subprocess.run(["ffmpeg", "-y"] + args, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {proc.stderr[-300:]}")


async def _handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Voice-in / voice-out conversation loop:
      OGG download → MP3 → Groq transcription (Whisper fallback)
      → agent → TTS MP3 → OGG opus → reply_voice
    """
    if not await auth_middleware(update, context, cfg.allowed_users()):
        return

    msg = update.message
    if msg is None:
        return

    transcriber = context.bot_data.get("transcriber")
    if not transcriber:
        await msg.reply_text("⚠️ Transcription not available.")
        return

    user_id = update.effective_user.id
    agent = context.bot_data["agent"]
    audio_dir = Path("/opt/kovo/data/audio")

    try:
        # ── 1. Download OGG ───────────────────────────────────────────────────
        await msg.chat.send_action(ChatAction.RECORD_VOICE)
        tg_file = await context.bot.get_file(msg.voice.file_id)
        ogg_path = str(audio_dir / f"voice_{user_id}.ogg")
        await tg_file.download_to_drive(ogg_path)

        # ── 2. Convert OGG → MP3 ─────────────────────────────────────────────
        mp3_in = str(audio_dir / f"voice_{user_id}_in.mp3")
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, _ffmpeg, ["-i", ogg_path, "-q:a", "4", mp3_in]
            )
        except RuntimeError as e:
            log.error("OGG→MP3 conversion failed: %s", e)
            await msg.reply_text(f"❌ Audio conversion failed: {e}")
            return

        # ── 3. Transcribe (Groq primary, local Whisper fallback) ─────────────
        try:
            text = await transcriber.transcribe(mp3_in)
        except Exception as e:
            log.error("Transcription failed: %s", e)
            await msg.reply_text(f"❌ Transcription failed: {e}")
            return

        if not text:
            await msg.reply_text("⚠️ Could not transcribe audio — please try again.")
            return

        log.info("voice transcription: user=%s text=%r", user_id, text[:80])
        await msg.reply_text(f"🎤 _{text}_", parse_mode="Markdown")

        # ── 4. Agent ──────────────────────────────────────────────────────────
        await msg.chat.send_action(ChatAction.TYPING)
        result = await agent.handle(message=text, user_id=user_id)
        response_text = result.get("text", "(no response)")
        log.info("voice reply: user=%s model=%s len=%d", user_id, result.get("model_used", "?"), len(response_text))

        # ── 5. Handle any [SEND_IMAGE: ...] tags ─────────────────────────────
        response_text = await _handle_image_tags(update, response_text)

        # ── 6. TTS → MP3 → OGG opus → reply_voice (cap at 800 chars) ─────────
        tts = getattr(agent, "tts", None)
        tts_text = response_text[:800]
        if tts and tts_text:
            await msg.chat.send_action(ChatAction.RECORD_VOICE)
            try:
                mp3_out = await tts.speak(
                    tts_text,
                    output_path=str(audio_dir / f"voice_reply_{user_id}.mp3"),
                )
                ogg_out = str(audio_dir / f"voice_reply_{user_id}.ogg")
                await asyncio.get_event_loop().run_in_executor(
                    None, _ffmpeg,
                    ["-i", mp3_out, "-c:a", "libopus", "-b:a", "48k", ogg_out],
                )
                await msg.reply_voice(voice=open(ogg_out, "rb"))
            except Exception as e:
                log.error("TTS/voice reply failed: %s", e)

        # Always send text too — voice + text together (the owner's preference)
        for i in range(0, max(len(response_text), 1), 4096):
            chunk = response_text[i : i + 4096]
            if chunk:
                await msg.reply_text(chunk)

    except Exception as e:
        log.error("_handle_voice error (user=%s): %s", user_id, e, exc_info=True)
        try:
            await msg.reply_text(f"❌ Voice handler error: {e}")
        except Exception:
            pass


def _extract_text(msg) -> str:
    """Extract text from any message type (text, caption, etc.). Never raises."""
    if msg is None:
        return ""
    return (getattr(msg, "text", None) or getattr(msg, "caption", None) or "").strip()


async def _reply_with_retry(msg, text: str, retries: int = 3, reply_markup=None) -> None:
    """Send reply_text with retry on transient network errors."""
    import asyncio
    from telegram.error import NetworkError, TimedOut
    for attempt in range(retries):
        try:
            await msg.reply_text(text, reply_markup=reply_markup)
            return
        except (NetworkError, TimedOut) as e:
            if attempt == retries - 1:
                raise
            log.warning("reply_text attempt %d failed (%s), retrying...", attempt + 1, e)
            await asyncio.sleep(1.5 * (attempt + 1))


async def _handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await auth_middleware(update, context, cfg.allowed_users()):
        return

    msg = update.message
    if msg is None:
        return

    try:
        message_text = _extract_text(msg)

        # When the owner uses Telegram's reply/quote feature, include the quoted
        # message as context so the agent knows what's being referred to.
        reply = msg.reply_to_message
        if reply is not None:
            quoted_text = _extract_text(reply)
            if quoted_text:
                if message_text:
                    # Prepend quoted context to the owner's reply
                    message_text = f'[Quoting: "{quoted_text[:400]}"]\n{message_text}'
                else:
                    # Replied with no new text — treat the quoted text as the message
                    message_text = quoted_text

        if not message_text:
            await msg.reply_text("Send me a text message.")
            return

        # ── Intercept code for pending /auth_google flow ─────────────────────
        if "google_auth_state" in context.user_data:
            await _handle_google_auth_code(update, context, message_text)
            return

        # ── Intercept OTP for pending /reauth_caller flow ────────────────────
        if "reauth_state" in context.user_data:
            await _handle_reauth_otp(update, context, message_text)
            return

        # ── Clear pending purge when user sends any non-/purge message ───────
        if "pending_purge" in context.bot_data:
            context.bot_data.pop("pending_purge", None)

        # ── Onboarding intercept ─────────────────────────────────────────────
        onboarding = context.bot_data.get("onboarding")
        if onboarding is not None:
            if onboarding.is_subagent_active():
                result = await onboarding.handle_subagent_message(
                    message_text,
                    send_fn=lambda t: msg.reply_text(t, parse_mode="Markdown"),
                )
                if result is not None:
                    log.info("Sub-agent creation complete: %s", result.get("name"))
                return
            if onboarding.is_active():
                await onboarding.handle(
                    message_text,
                    send_fn=lambda t: msg.reply_text(t, parse_mode="Markdown"),
                )
                return

        user_id = update.effective_user.id
        agent = context.bot_data["agent"]

        # Honour one-shot model override set by /model command
        force_complexity = None
        force_model = context.user_data.pop("force_model", None)
        if force_model == "sonnet":
            force_complexity = "medium"
        elif force_model == "opus":
            force_complexity = "complex"

        await msg.chat.send_action(ChatAction.TYPING)

        result = await agent.handle(
            message=message_text,
            user_id=user_id,
            force_complexity=force_complexity,
        )

        # Permission-needed: store state and show inline approve/deny buttons
        if result.get("__permission_needed__"):
            pattern = result["pattern"]
            blocked_cmd = result.get("blocked_command", pattern)
            context.bot_data["pending_permission"] = {
                "message":         message_text,
                "user_id":         user_id,
                "pattern":         pattern,
                "blocked_command": blocked_cmd,
                "force_complexity": force_complexity,
            }
            await msg.reply_text(
                f"🔒 *Permission Request*\n\n"
                f"Command: `{blocked_cmd}`\n"
                f"Pattern: `{pattern}`\n\n"
                f"This permanently allows `{blocked_cmd.split()[0]}` commands.",
                parse_mode="Markdown",
                reply_markup=perm_inline(),
            )
            return

        response_text = result.get("text", "(no response)")
        model_used = result.get("model_used", "?")
        agent_used = result.get("agent", "kovo")
        log.info("user=%s agent=%s model=%s len=%d", user_id, agent_used, model_used, len(response_text))

        # Handle any [SEND_IMAGE: ...] tags before sending text
        response_text = await _handle_image_tags(update, response_text)

        # Sub-agent recommendation → store pending + attach inline button to last chunk
        sub_topic = result.get("__sub_agent_topic__")
        if sub_topic:
            context.bot_data["pending_agent"] = {"topic": sub_topic}

        # Send in 4096-char chunks; attach MAIN_KEYBOARD (or agent_inline) to last chunk
        chunks = [response_text[i : i + 4096] for i in range(0, max(len(response_text), 1), 4096)]
        for idx, chunk in enumerate(chunks):
            if chunk:
                is_last = (idx == len(chunks) - 1)
                if is_last:
                    markup = agent_inline() if sub_topic else MAIN_KEYBOARD
                else:
                    markup = None
                await _reply_with_retry(msg, chunk, reply_markup=markup)

    except Exception as e:
        log.error("_handle_message error (user=%s): %s", update.effective_user.id if update.effective_user else "?", e, exc_info=True)
        try:
            await msg.reply_text(f"❌ Something went wrong: {e}")
        except Exception:
            pass


async def _handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle incoming photos via Claude vision.
    Downloads the image, base64-encodes it (resizing if > 5 MB),
    and sends it to the Anthropic Messages API with the user's caption as the prompt.
    """
    if not await auth_middleware(update, context, cfg.allowed_users()):
        return

    msg = update.message
    if msg is None:
        return

    try:
        await msg.chat.send_action(ChatAction.TYPING)

        photo = msg.photo[-1]  # highest resolution
        tg_file = await context.bot.get_file(photo.file_id)
        data_dir = Path("/opt/kovo/data/photos")
        data_dir.mkdir(parents=True, exist_ok=True)
        user_id = update.effective_user.id
        photo_path = str(data_dir / f"photo_{user_id}_{photo.file_id[:8]}.jpg")
        await tg_file.download_to_drive(photo_path)

        caption = msg.caption or ""
        prompt = caption if caption else "Describe what you see in this image and respond helpfully."

        agent = context.bot_data["agent"]
        result = await agent.handle_image(
            image_path=photo_path,
            prompt=prompt,
            user_id=user_id,
        )

        response_text = result.get("text", "(no response)")
        response_text = await _handle_image_tags(update, response_text)
        for i in range(0, max(len(response_text), 1), 4096):
            chunk = response_text[i : i + 4096]
            if chunk:
                await _reply_with_retry(msg, chunk)

    except Exception as e:
        log.error("_handle_photo error (user=%s): %s", update.effective_user.id if update.effective_user else "?", e, exc_info=True)
        try:
            await msg.reply_text(f"❌ Couldn't process your photo: {e}")
        except Exception:
            pass


# Extensions that can be read as plain text and included directly in the prompt
_TEXT_EXTENSIONS = {
    ".txt", ".md", ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css",
    ".json", ".yaml", ".yml", ".csv", ".xml", ".sh", ".bash", ".sql",
    ".log", ".rst", ".ini", ".toml", ".conf", ".env",
}
_MAX_TEXT_INLINE = 40_000  # characters — cap to avoid huge prompts


async def _handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle incoming documents:
    - Text files (.py, .md, .txt, .json, etc.) → read content, include in prompt.
    - PDFs, DOCX, and other binaries → pass via --file for Claude to analyse.
    Caption (if any) is always used as the user's instruction.
    """
    if not await auth_middleware(update, context, cfg.allowed_users()):
        return

    msg = update.message
    if msg is None:
        return

    try:
        await msg.chat.send_action(ChatAction.TYPING)

        doc = msg.document
        filename = doc.file_name or "document"
        caption = msg.caption or ""
        user_id = update.effective_user.id
        agent = context.bot_data["agent"]

        docs_dir = Path("/opt/kovo/data/documents")
        docs_dir.mkdir(parents=True, exist_ok=True)
        tg_file = await context.bot.get_file(doc.file_id)
        file_path = docs_dir / f"{user_id}_{filename}"
        await tg_file.download_to_drive(str(file_path))

        suffix = file_path.suffix.lower()

        if suffix in _TEXT_EXTENSIONS:
            # Read content and include inline — no --file needed
            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
                if len(content) > _MAX_TEXT_INLINE:
                    content = content[:_MAX_TEXT_INLINE] + f"\n\n… (truncated at {_MAX_TEXT_INLINE} chars)"
            except Exception as read_err:
                content = f"(could not read file: {read_err})"

            instruction = caption if caption else "Summarize or explain this file."
            prompt = f"[File: {filename}]\n{instruction}\n\n```\n{content}\n```"
            result = await agent.handle(
                message=prompt,
                user_id=user_id,
                force_complexity="complex",
            )
        else:
            # Binary file (PDF, DOCX, etc.) — pass via --file
            instruction = caption if caption else "Summarize or analyze this document."
            prompt = f"[File: {filename}] {instruction}"
            result = await agent.handle(
                message=prompt,
                user_id=user_id,
                force_complexity="complex",
                files=[str(file_path)],
            )

        response_text = result.get("text", "(no response)")
        response_text = await _handle_image_tags(update, response_text)
        for i in range(0, max(len(response_text), 1), 4096):
            chunk = response_text[i : i + 4096]
            if chunk:
                await _reply_with_retry(msg, chunk)

    except Exception as e:
        log.error("_handle_document error (user=%s): %s", update.effective_user.id if update.effective_user else "?", e, exc_info=True)
        try:
            await msg.reply_text(f"❌ Couldn't process your document: {e}")
        except Exception:
            pass


async def _handle_unsupported_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Polite acknowledgement for media types the bot doesn't process (stickers, videos, etc.)."""
    if not await auth_middleware(update, context, cfg.allowed_users()):
        return

    msg = update.message
    if msg is None:
        return

    if msg.sticker:
        media_type = f"sticker ({msg.sticker.emoji or ''})"
    elif msg.video:
        dur = f", {msg.video.duration}s" if msg.video.duration else ""
        media_type = f"video{dur}"
    elif msg.animation:
        media_type = "GIF"
    elif msg.contact:
        name = f"{msg.contact.first_name or ''} {msg.contact.last_name or ''}".strip()
        media_type = f"contact ({name})" if name else "contact"
    elif msg.location:
        media_type = f"location ({msg.location.latitude:.4f}, {msg.location.longitude:.4f})"
    elif msg.audio:
        media_type = f"audio file ({msg.audio.file_name or 'audio'})"
    elif msg.video_note:
        media_type = "video note"
    else:
        media_type = "media"

    caption = msg.caption or ""
    if caption:
        reply = f"I received your {media_type}. You said: \"{caption}\". What would you like me to do with it?"
    else:
        reply = f"I received your {media_type}. What would you like me to do with it?"

    await msg.reply_text(reply)


async def _handle_approve(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /approve — grant the pending permission request and retry the original task.
    Only the authorised user can do this.
    """
    if not await auth_middleware(update, context, cfg.allowed_users()):
        return

    pending = context.bot_data.get("pending_permission")
    if not pending:
        await update.message.reply_text("No pending permission request.")
        return

    pattern = pending["pattern"]
    from src.tools.claude_cli import add_permission
    if not add_permission(pattern):
        await update.message.reply_text(f"❌ Failed to add `{pattern}` — check logs.")
        return

    await update.message.reply_text(
        f"✅ Added `{pattern}` to my permissions. Retrying…",
        parse_mode="Markdown",
    )

    # Clear pending before retry so a nested permission error creates a fresh request
    context.bot_data.pop("pending_permission", None)

    # Retry the original task
    agent = context.bot_data.get("agent")
    if not agent:
        await update.message.reply_text("Agent not available for retry.")
        return

    await update.message.chat.send_action(ChatAction.TYPING)
    result = await agent.handle(
        message=pending["message"],
        user_id=pending["user_id"],
        force_complexity=pending.get("force_complexity"),
    )

    # Another permission error on retry — set up a new request with inline buttons
    if result.get("__permission_needed__"):
        pattern2   = result["pattern"]
        blocked_cmd2 = result.get("blocked_command", pattern2)
        context.bot_data["pending_permission"] = {
            "message":         pending["message"],
            "user_id":         pending["user_id"],
            "pattern":         pattern2,
            "blocked_command": blocked_cmd2,
            "force_complexity": pending.get("force_complexity"),
        }
        await update.message.reply_text(
            f"🔒 *Another permission needed*\n\n"
            f"Command: `{blocked_cmd2}`\nPattern: `{pattern2}`",
            parse_mode="Markdown",
            reply_markup=perm_inline(),
        )
        return

    response_text = result.get("text", "(no response)")
    response_text = await _handle_image_tags(update, response_text)
    chunks = [response_text[i : i + 4096] for i in range(0, max(len(response_text), 1), 4096)]
    for idx, chunk in enumerate(chunks):
        if chunk:
            markup = MAIN_KEYBOARD if idx == len(chunks) - 1 else None
            await _reply_with_retry(update.message, chunk, reply_markup=markup)


async def _handle_deny(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/deny — reject the pending permission request."""
    if not await auth_middleware(update, context, cfg.allowed_users()):
        return

    pending = context.bot_data.pop("pending_permission", None)
    if not pending:
        await update.message.reply_text("No pending permission request.")
        return

    pattern = pending.get("pattern", "")
    log.info("Permission denied by user for pattern: %s", pattern)
    from src.tools.claude_cli import deny_permission
    deny_permission(pattern)
    await update.message.reply_text("Got it. I'll find another way or skip this step.")


async def _error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Global error handler — log and swallow all exceptions so the bot never crashes.
    Network blips (ConnectError, TimedOut) are expected and should not restart the service.
    """
    from telegram.error import NetworkError, TimedOut, RetryAfter
    err = context.error
    if isinstance(err, (NetworkError, TimedOut)):
        log.warning("Telegram network error (transient): %s", err)
    elif isinstance(err, RetryAfter):
        log.warning("Telegram rate limit — retry after %ss", err.retry_after)
    else:
        log.error("Unhandled bot error: %s", err, exc_info=err)


# Map keyboard button labels → command handler functions (wired in build_application)
_BUTTON_HANDLERS: dict = {}


async def _handle_keyboard_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route emoji-label keyboard button taps to the appropriate command handler."""
    if not await auth_middleware(update, context, cfg.allowed_users()):
        return
    msg = update.message
    if msg is None:
        return
    handler_fn = _BUTTON_HANDLERS.get(msg.text or "")
    if handler_fn:
        await handler_fn(update, context)


def build_application(
    agent,
    ollama,
    memory,
    skills,
    creator,
    tool_registry,
    transcriber=None,
    onboarding=None,
    storage=None,
    structured_store=None,
    auto_extractor=None,
) -> Application:
    """Create and configure the Telegram bot application."""
    app = Application.builder().token(cfg.telegram_token()).build()

    # Shared objects — available via context.bot_data in all handlers
    app.bot_data["agent"] = agent
    app.bot_data["ollama"] = ollama
    app.bot_data["memory"] = memory
    app.bot_data["skills"] = skills
    app.bot_data["creator"] = creator
    app.bot_data["tool_registry"] = tool_registry
    app.bot_data["transcriber"] = transcriber      # None if not configured
    app.bot_data["onboarding"] = onboarding        # None after first-run completes
    app.bot_data["storage"] = storage              # None if not configured
    app.bot_data["structured_store"] = structured_store  # SQLite store
    app.bot_data["auto_extractor"] = auto_extractor     # memory extractor

    # Commands
    app.add_handler(CommandHandler("start", cmd.cmd_start))
    app.add_handler(CommandHandler("status", cmd.cmd_status))
    app.add_handler(CommandHandler("tools", cmd.cmd_tools))
    app.add_handler(CommandHandler("agents", cmd.cmd_agents))
    app.add_handler(CommandHandler("model", cmd.cmd_model))
    app.add_handler(CommandHandler("memory", cmd.cmd_memory))
    app.add_handler(CommandHandler("skills", cmd.cmd_skills))
    app.add_handler(CommandHandler("health", cmd.cmd_health))
    app.add_handler(CommandHandler("flush", cmd.cmd_flush))
    app.add_handler(CommandHandler("newskill", cmd.cmd_newskill))
    app.add_handler(CommandHandler("clear", cmd.cmd_clear))
    app.add_handler(CommandHandler("call", cmd.cmd_call))
    app.add_handler(CommandHandler("auth_google", cmd.cmd_auth_google))
    app.add_handler(CommandHandler("auth_github", cmd.cmd_auth_github))
    app.add_handler(CommandHandler("reauth_caller", cmd.cmd_reauth_caller))
    app.add_handler(CommandHandler("search", cmd.cmd_search))
    app.add_handler(CommandHandler("permissions", cmd.cmd_permissions))
    app.add_handler(CommandHandler("approve", _handle_approve))
    app.add_handler(CommandHandler("deny", _handle_deny))
    app.add_handler(CommandHandler("storage", cmd.cmd_storage))
    app.add_handler(CommandHandler("purge", cmd.cmd_purge))
    app.add_handler(CommandHandler("db", cmd.cmd_db))

    # Inline keyboard callbacks (permission, purge, sub-agent buttons)
    app.add_handler(CallbackQueryHandler(cmd.button_callback))

    # Wire keyboard button text → command functions (after cmd is imported)
    _BUTTON_HANDLERS.update({
        "📡 Status":  cmd.cmd_status,
        "🖥 Health":  cmd.cmd_health,
        "🧠 Memory":  cmd.cmd_memory,
        "💾 Storage": cmd.cmd_storage,
        "📚 Skills":  cmd.cmd_skills,
        "🔧 Tools":   cmd.cmd_tools,
    })

    # Keyboard button handler — must be registered BEFORE the general text handler
    import re as _re
    _btn_pattern = _re.compile(
        r"^(📡 Status|🖥 Health|🧠 Memory|💾 Storage|📚 Skills|🔧 Tools)$"
    )
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(_btn_pattern),
        _handle_keyboard_button,
    ))

    # Media handlers — ordered by specificity (voice/photo/document before fallback)
    app.add_handler(MessageHandler(filters.VOICE, _handle_voice))
    app.add_handler(MessageHandler(filters.PHOTO, _handle_photo))
    app.add_handler(MessageHandler(filters.Document.ALL, _handle_document))

    # Unsupported media — polite reply, no crash
    _unsupported = (
        filters.Sticker.ALL
        | filters.VIDEO
        | filters.ANIMATION
        | filters.CONTACT
        | filters.LOCATION
        | filters.AUDIO
        | filters.VIDEO_NOTE
    )
    app.add_handler(MessageHandler(_unsupported, _handle_unsupported_media))

    # All plain text messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _handle_message))

    # Global error handler — prevents network blips from crashing the service
    app.add_error_handler(_error_handler)

    return app
