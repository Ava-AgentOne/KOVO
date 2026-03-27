"""
Generates workspace configuration files from onboarding state.

Called by OnboardingFlow._phase_generate after all data is collected.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date
from functools import partial
from pathlib import Path

log = logging.getLogger(__name__)

_STYLE_EMOJI = {
    "professional": "🎯",
    "friendly":     "😊",
    "sarcastic":    "😏",
    "minimal":      "⚡",
    "custom":       "🤖",
}


async def generate_all(state: dict, workspace_dir: Path, ollama_url: str) -> None:
    """Generate all workspace config files from onboarding state."""
    agent_name = state.get("agent_name", "Assistant")
    user_profile = state.get("user_profile") or {}
    personality = state.get("personality") or {}
    today = date.today().isoformat()

    loop = asyncio.get_event_loop()

    # SOUL.md is LLM-generated (async)
    await _generate_soul(agent_name, user_profile, personality, workspace_dir)

    # Remaining files are pure Python writes — run in executor to stay non-blocking
    await loop.run_in_executor(
        None, _write_identity, workspace_dir, agent_name, personality, today
    )
    await loop.run_in_executor(None, _write_user, workspace_dir, user_profile)
    await loop.run_in_executor(
        None, _write_memory, workspace_dir, agent_name, user_profile, ollama_url, today
    )

    log.info(
        "Onboarding generation complete — agent=%r user=%r",
        agent_name, user_profile.get("name"),
    )


async def _generate_soul(
    agent_name: str,
    user_profile: dict,
    personality: dict,
    workspace_dir: Path,
) -> None:
    """Generate SOUL.md using Claude; falls back to a hardcoded template on failure."""
    style = personality.get("style", "friendly")
    custom_desc = personality.get("custom_description") or ""
    emoji_usage = personality.get("emoji_usage", "sometimes")
    proactive = personality.get("proactive", True)
    user_name = user_profile.get("name") or "the user"
    occupation = user_profile.get("occupation") or ""
    city = user_profile.get("city") or ""
    country = user_profile.get("country") or ""

    style_desc = custom_desc or style
    proactive_line = (
        "Proactive — suggest improvements and spot things without being asked."
        if proactive
        else "Reactive — answer questions; don't volunteer unsolicited advice."
    )
    emoji_line = {
        "lots":      "Use emojis liberally to keep messages lively.",
        "sometimes": "Use emojis occasionally to add warmth, not in every message.",
        "never":     "Never use emojis. Plain text only.",
    }.get(emoji_usage, "Use emojis occasionally.")

    prompt = (
        f"Write a SOUL.md file for an AI assistant named {agent_name}.\n"
        f"The user's name is {user_name}, based in {city}, {country}.\n"
        f"Occupation: {occupation or 'not specified'}.\n"
        f"Personality style: {style_desc}.\n"
        f"Emoji policy: {emoji_line}\n"
        f"Proactivity: {proactive_line}\n\n"
        f"Use this exact structure:\n\n"
        f"# SOUL.md\n\n"
        f"You are {agent_name}, {user_name}'s personal AI assistant.\n\n"
        f"## Core Truths\n"
        f"(3-5 bullet points reflecting the personality and style)\n\n"
        f"## Personality\n"
        f"(3-5 bullet points)\n\n"
        f"## Boundaries\n"
        f"- Never share {user_name}'s personal information\n"
        f"- Never make financial transactions without explicit approval\n"
        f"- Never modify SOUL.md or IDENTITY.md without {user_name}'s permission\n"
        f"- Always log actions to daily memory\n\n"
        f"Output ONLY the markdown. No explanation, no code fences."
    )

    soul_text = None
    try:
        from src.tools.claude_cli import call_claude, extract_text
        loop = asyncio.get_event_loop()
        fn = partial(call_claude, prompt, model="sonnet", timeout=90)
        response = await loop.run_in_executor(None, fn)
        soul_text = extract_text(response).strip()
        # Sanity check — the generated file must not retain the unconfigured marker
        if not soul_text or "## UNCONFIGURED" in soul_text:
            log.warning("Claude returned unusable SOUL.md — falling back to template")
            soul_text = None
    except Exception as e:
        log.warning("Claude SOUL.md generation failed: %s — using fallback template", e)

    if not soul_text:
        soul_text = _fallback_soul(
            agent_name, user_name, style_desc, proactive_line, emoji_line
        )

    (workspace_dir / "SOUL.md").write_text(soul_text.rstrip() + "\n")
    log.info("SOUL.md written (%d chars)", len(soul_text))


def _fallback_soul(
    agent_name: str,
    user_name: str,
    style_desc: str,
    proactive_line: str,
    emoji_line: str,
) -> str:
    """Hardcoded template used when Claude is unavailable during generation."""
    return (
        f"# SOUL.md\n\n"
        f"You are {agent_name}, {user_name}'s personal AI assistant.\n\n"
        f"## Core Truths\n"
        f"- **Results Over Process** — Don't explain what you're going to do. Just do it.\n"
        f"- **Ownership** — When you take on a task, you own it end-to-end.\n"
        f"- **Honesty** — If you can't do something, say so. Then suggest an alternative.\n"
        f"- **Style** — {style_desc.capitalize()}.\n"
        f"- **Safety** — Dangerous operations require {user_name}'s confirmation via Telegram.\n\n"
        f"## Personality\n"
        f"- {proactive_line}\n"
        f"- {emoji_line}\n"
        f"- Technical but not condescending\n"
        f"- Remembers context from past conversations\n\n"
        f"## Boundaries\n"
        f"- Never share {user_name}'s personal information\n"
        f"- Never make financial transactions without explicit approval\n"
        f"- Never modify SOUL.md or IDENTITY.md without {user_name}'s permission\n"
        f"- Always log actions to daily memory"
    )


def _write_identity(
    workspace_dir: Path,
    agent_name: str,
    personality: dict,
    today: str,
) -> None:
    """Write IDENTITY.md — agent name, style, and creation metadata."""
    style = personality.get("style", "friendly")
    emoji = _STYLE_EMOJI.get(style, "🤖")
    custom_desc = personality.get("custom_description") or ""
    style_label = custom_desc or style.capitalize()
    emoji_usage = personality.get("emoji_usage", "sometimes")
    proactive = personality.get("proactive", True)

    voice_lines = {
        "professional": "Write with confidence and directness. No filler words.",
        "friendly":     "Write warmly and conversationally, like texting a smart friend.",
        "sarcastic":    "Write with dry wit and a hint of sarcasm — but always get the job done.",
        "minimal":      "Be extremely terse. Answer only what is asked. No pleasantries.",
        "custom":       custom_desc or "Write according to your configured style.",
    }
    voice = voice_lines.get(style, voice_lines["friendly"])

    content = (
        f"# IDENTITY.md\n\n"
        f"## Agent Identity\n"
        f"- **Name**: {agent_name}\n"
        f"- **Style**: {emoji} {style_label}\n"
        f"- **Emoji usage**: {emoji_usage}\n"
        f"- **Proactive**: {'Yes' if proactive else 'No'}\n"
        f"- **Created**: {today}\n\n"
        f"## Voice\n"
        f"{voice}\n"
    )

    (workspace_dir / "IDENTITY.md").write_text(content)
    log.info("IDENTITY.md written")


def _write_user(workspace_dir: Path, profile: dict) -> None:
    """Write USER.md — everything Kovo knows about the user."""
    name = profile.get("name") or "Unknown"
    city = profile.get("city") or "Unknown"
    country = profile.get("country") or "Unknown"
    tz = profile.get("timezone") or "UTC"
    langs = profile.get("languages") or "English"
    occ = profile.get("occupation") or "Not specified"
    email = profile.get("email") or "Not provided"

    content = (
        f"# USER.md\n\n"
        f"## Profile\n"
        f"- **Name**: {name}\n"
        f"- **Location**: {city}, {country}\n"
        f"- **Timezone**: {tz}\n"
        f"- **Languages**: {langs}\n"
        f"- **Occupation**: {occ}\n"
        f"- **Email**: {email}\n\n"
        f"## Preferences\n"
        f"(Add personalised preferences here as you learn them)\n\n"
        f"## Important Context\n"
        f"(Key facts that help you assist {name} effectively)\n"
    )

    (workspace_dir / "USER.md").write_text(content)
    log.info("USER.md written")


def _write_memory(
    workspace_dir: Path,
    agent_name: str,
    profile: dict,
    ollama_url: str,
    today: str,
) -> None:
    """Write MEMORY.md — initial bootstrap memory log."""
    user_name = profile.get("name") or "User"
    city = profile.get("city") or ""
    country = profile.get("country") or ""
    tz = profile.get("timezone") or "UTC"
    location = ", ".join(part for part in (city, country) if part) or "Unknown"

    content = (
        f"# MEMORY.md\n\n"
        f"## {today}\n"
        f"- First-run onboarding completed\n"
        f"- Agent configured as: {agent_name}\n"
        f"- User: {user_name} ({location}, {tz})\n"
        f"- All workspace files initialised: SOUL.md, USER.md, IDENTITY.md, MEMORY.md\n"
    )

    (workspace_dir / "MEMORY.md").write_text(content)
    log.info("MEMORY.md written")


def generate_subagent_files(config: dict, workspace_dir: Path) -> None:
    """
    Create a minimal sub-agent directory under workspace/agents/{name}/.

    Expected config keys: name, personality, instructions, task_type
    """
    name = config["name"]
    personality = config.get("personality") or "Professional and focused."
    instructions = config.get("instructions") or ""
    task_type = config.get("task_type") or "general"
    today = date.today().isoformat()

    agent_dir = workspace_dir / "agents" / name.lower()
    agent_dir.mkdir(parents=True, exist_ok=True)

    soul = (
        f"# SOUL.md — {name}\n\n"
        f"You are {name}, a specialised sub-agent.\n"
        f"Task focus: {task_type}\n"
        f"Created: {today}\n\n"
        f"## Personality\n"
        f"{personality}\n\n"
        f"## Instructions\n"
        f"{instructions or 'Handle tasks related to your focus area efficiently.'}\n\n"
        f"## Boundaries\n"
        f"- Escalate to the main agent for anything outside your task focus\n"
        f"- Never make irreversible changes without confirmation\n"
        f"- Always log significant actions\n"
    )

    (agent_dir / "SOUL.md").write_text(soul)
    log.info("Sub-agent %r created at %s", name, agent_dir)
