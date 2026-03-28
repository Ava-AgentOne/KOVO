"""
Onboarding state machine — guides new users through configuring their agent.

States: welcome → naming → user_profile → personality → confirm → generate → done

State is persisted to workspace/.onboarding_state.json so the flow resumes
correctly if the bot restarts mid-onboarding.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from functools import partial
from pathlib import Path
from typing import Awaitable, Callable

from src.tools.claude_cli import call_claude, extract_text

log = logging.getLogger(__name__)

SendFn = Callable[[str], Awaitable[None]]

# Personality style → emoji for IDENTITY.md
_STYLE_EMOJI = {
    "professional": "🎯",
    "friendly":     "😊",
    "sarcastic":    "😏",
    "minimal":      "⚡",
    "custom":       "🤖",
}

# Sensible defaults when the user types /skip
_DEFAULTS: dict = {
    "agent_name": "Assistant",
    "user_profile": {
        "name":       "User",
        "languages":  "English",
        "occupation": "Not specified",
        "email":      None,
    },
    "personality": {
        "style":              "friendly",
        "custom_description": None,
        "emoji_usage":        "sometimes",
        "proactive":          True,
    },
}


class OnboardingFlow:
    """
    First-run setup state machine.

    Instantiate once at startup (gateway/main.py) and store in bot_data.
    is_active() returns False for already-configured systems — zero overhead.
    """

    def __init__(self, workspace_dir: Path) -> None:
        self._workspace = workspace_dir
        self._state_file = workspace_dir / ".onboarding_state.json"
        self._state: dict = self._load_state()
        # Sub-agent onboarding runs in parallel, with its own in-memory state
        self._subagent_state: dict | None = None

    # ── Public API ─────────────────────────────────────────────────────────

    @staticmethod
    def should_run(workspace_dir: Path) -> bool:
        """True if SOUL.md contains the ## UNCONFIGURED marker."""
        soul = workspace_dir / "SOUL.md"
        try:
            return soul.exists() and "## UNCONFIGURED" in soul.read_text()
        except Exception:
            return False

    def is_active(self) -> bool:
        """True while the main onboarding flow is in progress."""
        return self._state.get("phase") not in (None, "done")

    def is_subagent_active(self) -> bool:
        """True while a sub-agent creation conversation is in progress."""
        return self._subagent_state is not None

    async def handle(self, message: str, send_fn: SendFn) -> None:
        """Route an incoming message to the current phase handler."""
        # /skip jumps straight to generate with whatever we have so far
        if message.strip().lower() in ("/skip", "skip"):
            await self._apply_skip(send_fn)
            return

        phase = self._state.get("phase", "welcome")
        handler = {
            "welcome":      self._phase_welcome,
            "naming":       self._phase_naming,
            "user_profile": self._phase_user_profile,
            "personality":  self._phase_personality,
            "confirm":      self._phase_confirm,
            "generate":     self._phase_generate,
        }.get(phase)

        if handler:
            await handler(message, send_fn)
        else:
            log.warning("Onboarding: unrecognised phase %r", phase)

    async def start_subagent_onboarding(
        self, task_type: str, suggestion: str, send_fn: SendFn
    ) -> None:
        """
        Begin a 3-question sub-agent creation conversation.
        task_type: e.g. "devops", "finance" — used for naming hints.
        suggestion: auto-suggested name, e.g. "DevOpsAgent".
        """
        self._subagent_state = {
            "phase":       "name",
            "task_type":   task_type,
            "suggestion":  suggestion,
        }
        await send_fn(
            f"🤖 *Creating a sub-agent*\n\n"
            f"Suggested name: *{suggestion}*\n\n"
            f"What should I call this agent? "
            f"(reply with a name, or say 'use {suggestion}' to accept)"
        )

    async def handle_subagent_message(
        self, message: str, send_fn: SendFn
    ) -> dict | None:
        """
        Process one message in the sub-agent creation flow.
        Returns the config dict when the flow is complete, else None.
        """
        if not self._subagent_state:
            return None

        phase = self._subagent_state.get("phase")

        if phase == "name":
            name = _extract_name(message) or self._subagent_state["suggestion"]
            self._subagent_state["name"] = name
            self._subagent_state["phase"] = "personality"
            await send_fn(
                f"*{name}* — noted!\n\n"
                f"Personality for this agent?\n\n"
                f"• *Inherit* — same style as me\n"
                f"• *Professional* — focused, no-nonsense\n"
                f"• *Custom* — describe your own"
            )
            return None

        if phase == "personality":
            self._subagent_state["personality"] = message.strip()
            self._subagent_state["phase"] = "instructions"
            await send_fn(
                "Any special instructions or focus areas for this agent? "
                "(or say 'none')"
            )
            return None

        if phase == "instructions":
            raw = message.strip()
            self._subagent_state["instructions"] = "" if raw.lower() == "none" else raw
            config = await self._finish_subagent(send_fn)
            self._subagent_state = None
            return config

        return None

    # ── Main phase handlers ────────────────────────────────────────────────

    async def _phase_welcome(self, message: str, send_fn: SendFn) -> None:
        self._set_state({"phase": "naming"})
        await send_fn(
            "🎉 Hey there! I just woke up on your server and I'm ready to become "
            "your personal AI assistant.\n\n"
            "But first — I need a name! What would you like to call me?\n\n"
            "Some ideas: Jarvis, Friday, Atlas, Nova, Echo, Sage... "
            "or anything you like."
        )

    async def _phase_naming(self, message: str, send_fn: SendFn) -> None:
        agent_name = _extract_name(message) or "Assistant"
        self._set_state({**self._state, "phase": "user_profile", "agent_name": agent_name})
        await send_fn(
            f"*{agent_name}* — I like it! ✨\n\n"
            f"Now let me get to know you. Answer these quick questions "
            f"(all at once or one by one):\n\n"
            f"1️⃣ What's your name?\n"
            f"2️⃣ What languages do you speak?\n"
            f"3️⃣ What do you do? (job, hobby, or just \"student\")\n"
            f"4️⃣ Email address? (for Google integration — say \"skip\" to skip)"
        )

    async def _phase_user_profile(self, message: str, send_fn: SendFn) -> None:
        profile = await self._extract_user_profile(message)

        # Re-prompt if critical fields are missing
        if not profile.get("name"):
            await send_fn(
                "I didn't quite catch your name. Could you tell me at least:\n\n"
                "• Your name\n\n"
                "(Everything else is optional)"
            )
            return

        self._set_state({**self._state, "phase": "personality", "user_profile": profile})

        name = profile.get("name", "—")
        langs = profile.get("languages", "—")
        occ = profile.get("occupation", "—")
        email = profile.get("email") or "skipped"

        await send_fn(
            f"Nice to meet you, *{name}*! Here's what I've got:\n\n"
            f"👤 {name}\n"
            f"🗣️ {langs}\n"
            f"💼 {occ}\n"
            f"📧 {email}\n\n"
            f"Now the fun part — how should I talk to you?\n\n"
            f"🎯 *Professional* — Clean, concise, no fluff\n"
            f"😄 *Friendly* — Casual, warm, like texting a smart friend\n"
            f"😏 *Sarcastic* — Gets things done but with humor\n"
            f"🤖 *Minimal* — Just answers. No small talk\n"
            f"🎨 *Custom* — Describe your own style\n\n"
            f"Also tell me:\n"
            f"• Emoji usage? (lots / sometimes / never)\n"
            f"• Should I be proactive? (suggest things without being asked?)"
        )

    async def _phase_personality(self, message: str, send_fn: SendFn) -> None:
        personality = await self._extract_personality(message)
        self._set_state({**self._state, "phase": "confirm", "personality": personality})
        await self._send_confirmation(send_fn)

    async def _phase_confirm(self, message: str, send_fn: SendFn) -> None:
        msg_lower = message.lower().strip()
        confirm_words = {
            "yes", "yeah", "yep", "yup", "ok", "okay", "sure",
            "looks good", "confirm", "lock it", "lock it in",
            "go ahead", "do it", "perfect", "correct", "great",
        }
        if any(w in msg_lower for w in confirm_words):
            await self._phase_generate("", send_fn)
        else:
            # User wants to change something
            updates = await self._extract_correction(message)
            if updates:
                self._set_state({**self._state, **updates})
            await self._send_confirmation(send_fn)

    async def _phase_generate(self, message: str, send_fn: SendFn) -> None:
        # Update state to "generate" while keeping all collected data
        self._set_state({**self._state, "phase": "generate"})
        await send_fn("⚙️ Generating your configuration…")

        try:
            from src.onboarding.generator import generate_all
            from src.gateway import config as cfg
            await generate_all(self._state, self._workspace, cfg.ollama_url())
        except Exception as e:
            log.error("Onboarding generation failed: %s", e, exc_info=True)
            await send_fn(
                f"❌ Something went wrong: {e}\n\n"
                f"Type /skip to use sensible defaults and finish setup."
            )
            return

        # Capture data before clearing state
        agent_name = self._state.get("agent_name", "Assistant")
        user_name = (self._state.get("user_profile") or {}).get("name", "there")

        # Mark done — remove state file, keep only phase in memory
        self._state_file.unlink(missing_ok=True)
        self._state = {"phase": "done"}

        # Verify SOUL.md no longer has the UNCONFIGURED marker
        if OnboardingFlow.should_run(self._workspace):
            log.error("Onboarding: SOUL.md still contains ## UNCONFIGURED after generation!")

        await send_fn(
            f"✅ All set! I'm *{agent_name}*, and I'm ready to work.\n\n"
            f"Here's what I can do:\n"
            f"💬 Chat and answer questions\n"
            f"🖥️ Run commands on your server\n"
            f"📊 Monitor system health and alert you\n"
            f"🌐 Browse the web and research\n"
            f"📞 Send voice call alerts for urgent matters\n\n"
            f"Type /help anytime, or just talk to me naturally. "
            f"What's first, *{user_name}*?"
        )

    # ── Skip ───────────────────────────────────────────────────────────────

    async def _apply_skip(self, send_fn: SendFn) -> None:
        """Fill any missing state with defaults and jump straight to generate."""
        d = _DEFAULTS
        self._set_state({
            "phase":        "generate",
            "agent_name":   self._state.get("agent_name") or d["agent_name"],
            "user_profile": self._state.get("user_profile") or d["user_profile"],
            "personality":  self._state.get("personality") or d["personality"],
        })
        await send_fn("⏩ Using defaults — setting up now…")
        await self._phase_generate("", send_fn)

    # ── Confirmation display ───────────────────────────────────────────────

    async def _send_confirmation(self, send_fn: SendFn) -> None:
        s = self._state
        agent_name = s.get("agent_name", "?")
        p = s.get("user_profile") or {}
        pers = s.get("personality") or {}

        style = pers.get("style", "friendly")
        style_desc = pers.get("custom_description") or style.capitalize()
        emoji_use = pers.get("emoji_usage", "sometimes")
        proactive = "Yes" if pers.get("proactive", True) else "No"

        await send_fn(
            f"*Perfect! Here's the full setup:*\n\n"
            f"🏷️ My name: *{agent_name}*\n"
            f"👤 Your name: {p.get('name', '—')}\n"
            f"🗣️ Languages: {p.get('languages', '—')}\n"
            f"💼 Role: {p.get('occupation', '—')}\n"
            f"📧 Email: {p.get('email') or 'skipped'}\n"
            f"🎭 My style: {style_desc}\n"
            f"😊 Emoji: {emoji_use}\n"
            f"⚡ Proactive: {proactive}\n\n"
            f"Does this look right? Say *yes* to lock it in, "
            f"or tell me what to change."
        )

    # ── Claude extractions ─────────────────────────────────────────────────

    async def _extract_user_profile(self, message: str) -> dict:
        system = (
            "Extract user profile from this message. "
            "Return JSON only, no markdown, no code fences: "
            '{"name":string|null,"languages":string|null,'
            '"occupation":string|null,"email":string|null}. '
            "Set email to null if missing or skipped. "
            "Set unknown fields to null."
        )
        try:
            loop = asyncio.get_event_loop()
            fn = partial(call_claude, message, model="sonnet",
                         system_prompt=system, timeout=60)
            response = await loop.run_in_executor(None, fn)
            text = _strip_fences(extract_text(response))
            data = json.loads(text)
            return {k: (v or None) for k, v in data.items()}
        except Exception as e:
            log.warning("User profile extraction failed: %s — message: %r", e, message[:80])
            return {}

    async def _extract_personality(self, message: str) -> dict:
        system = (
            "Extract personality preferences from this message. "
            "Return JSON only, no markdown, no code fences: "
            '{"style":"professional"|"friendly"|"sarcastic"|"minimal"|"custom",'
            '"custom_description":string|null,'
            '"emoji_usage":"lots"|"sometimes"|"never",'
            '"proactive":true|false}. '
            "Default emoji_usage to 'sometimes' and proactive to true if not stated."
        )
        try:
            loop = asyncio.get_event_loop()
            fn = partial(call_claude, message, model="sonnet",
                         system_prompt=system, timeout=60)
            response = await loop.run_in_executor(None, fn)
            text = _strip_fences(extract_text(response))
            return json.loads(text)
        except Exception as e:
            log.warning("Personality extraction failed: %s", e)
            return _DEFAULTS["personality"].copy()

    async def _extract_correction(self, message: str) -> dict:
        """Figure out what the user wants to change in the confirm state."""
        current = json.dumps({
            "agent_name":   self._state.get("agent_name"),
            "user_profile": self._state.get("user_profile"),
            "personality":  self._state.get("personality"),
        })
        system = (
            f"Current agent setup: {current}. "
            "The user wants to change something. "
            "Return JSON with ONLY the top-level keys that changed "
            "(agent_name, user_profile as partial dict, personality as partial dict). "
            "Return {} if nothing is clearly changing. "
            "No markdown, no code fences."
        )
        try:
            loop = asyncio.get_event_loop()
            fn = partial(call_claude, message, model="sonnet",
                         system_prompt=system, timeout=60)
            response = await loop.run_in_executor(None, fn)
            text = _strip_fences(extract_text(response))
            updates = json.loads(text)
            result: dict = {}
            if "agent_name" in updates:
                result["agent_name"] = updates["agent_name"]
            if "user_profile" in updates:
                result["user_profile"] = {
                    **(self._state.get("user_profile") or {}),
                    **updates["user_profile"],
                }
            if "personality" in updates:
                result["personality"] = {
                    **(self._state.get("personality") or {}),
                    **updates["personality"],
                }
            return result
        except Exception as e:
            log.warning("Correction extraction failed: %s", e)
            return {}

    # ── Sub-agent generation ───────────────────────────────────────────────

    async def _finish_subagent(self, send_fn: SendFn) -> dict:
        from src.onboarding.generator import generate_subagent_files

        sa = self._subagent_state
        name = sa["name"]
        personality_raw = sa.get("personality", "inherit")

        if "inherit" in personality_raw.lower():
            soul_text = ""
            try:
                soul_text = (self._workspace / "SOUL.md").read_text()[:500]
            except Exception:
                pass
            personality_desc = (
                f"Inherit from main agent:\n{soul_text}" if soul_text
                else "Professional and focused."
            )
        else:
            personality_desc = personality_raw

        config = {
            "name":         name,
            "personality":  personality_desc,
            "instructions": sa.get("instructions", ""),
            "task_type":    sa.get("task_type", "general"),
        }
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, generate_subagent_files, config, self._workspace
            )
            await send_fn(
                f"✅ Sub-agent *{name}* created in "
                f"`workspace/agents/{name.lower()}/`"
            )
        except Exception as e:
            log.error("Sub-agent generation failed: %s", e)
            await send_fn(f"❌ Failed to create sub-agent: {e}")

        return config

    # ── State persistence ──────────────────────────────────────────────────

    def _load_state(self) -> dict:
        """Load state from file, or infer initial state from SOUL.md."""
        try:
            if self._state_file.exists():
                data = json.loads(self._state_file.read_text())
                log.info("Onboarding: resuming from phase=%s", data.get("phase"))
                return data
        except Exception as e:
            log.warning("Onboarding: could not load state file: %s", e)
        # No state file — start onboarding only if SOUL.md has the marker
        if OnboardingFlow.should_run(self._workspace):
            log.info("Onboarding: SOUL.md has ## UNCONFIGURED — starting fresh")
            return {"phase": "welcome"}
        return {"phase": "done"}

    def _set_state(self, state: dict) -> None:
        self._state = state
        try:
            self._state_file.write_text(json.dumps(state, indent=2))
        except Exception as e:
            log.warning("Onboarding: could not persist state: %s", e)


# ── Module-level helpers ───────────────────────────────────────────────────────

def _extract_name(message: str) -> str | None:
    """
    Extract a single agent/person name from a free-form message.
    Works for "Call me Nova", "Nova", "I want Nova please", etc.
    """
    msg = message.strip()
    if not msg or len(msg) > 60:
        return None

    # Strip common preamble phrases
    msg = re.sub(
        r"^(?:call\s+(?:me|it|her|him)\s+|name\s+(?:me|it|her|him)\s+|"
        r"i\s+(?:want|like|choose|pick)\s+|how\s+about\s+|let'?s?\s+go\s+with\s+|"
        r"use\s+)",
        "", msg, flags=re.IGNORECASE
    ).strip()

    words = msg.split()
    if not words:
        return None

    # Single word or two words — capitalize and return
    if len(words) <= 2:
        return " ".join(w.capitalize() for w in words)

    # Scan for a capitalized word (proper name)
    for word in words:
        clean = re.sub(r"[^\w]", "", word)
        if clean and clean[0].isupper() and len(clean) >= 2:
            return clean

    return words[0].capitalize()


def _strip_fences(text: str) -> str:
    """Remove ```json ... ``` or ``` ... ``` wrappers from LLM output."""
    return re.sub(r"```(?:json)?\s*|\s*```", "", text).strip()
