"""
Kovo — the one and only main agent.

Handles everything directly. Has access to ALL tools.
Reads SOUL.md, USER.md always; loads MEMORY.md, daily logs,
matching skill, TOOLS.md, AGENTS.md only when relevant keywords detected.
Delegates to sub-agents when they exist.
Recommends creating sub-agents when it notices repeated specialised requests.
"""
from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from src.utils.platform import data_path
from src.utils.tz import get_tz as _get_configured_tz, today as _tz_today




if TYPE_CHECKING:
    from src.memory.manager import MemoryManager
    from src.router.model_router import ModelRouter
    from src.skills.registry import SkillRegistry
    from src.tools.registry import ToolRegistry
    from src.agents.sub_agent import SubAgentRunner

log = logging.getLogger(__name__)

# How many times a topic must appear before recommending a sub-agent
_PATTERN_THRESHOLD = 5

_TOPIC_KEYWORDS: dict[str, list[str]] = {
    "devops": ["docker", "container", "deploy", "k8s", "kubernetes", "ci", "cd", "pipeline", "nginx", "systemd"],
    "google_workspace": ["docs", "drive", "gmail", "email", "calendar", "google", "spreadsheet", "sheet"],
    "server_health": ["disk", "cpu", "ram", "memory", "unraid", "array", "health", "monitoring", "alert", "threshold"],
    "browser_automation": ["scrape", "website", "browse", "click", "form", "screenshot", "playwright", "automation"],
    "finance": ["expense", "budget", "invoice", "payment", "bank", "money", "cost", "price"],
}

# ── Context loading keyword sets ──────────────────────────────────────────────

_MEMORY_KW = frozenset([
    "remember", "decided", "prefer", "we agreed", "last time", "what did we",
    "what do i", "previously", "recall", "forgot", "you said", "you told",
    "i told you", "history", "do you know", "what did i", "you know that",
])
_LOG_KW = frozenset([
    "yesterday", "today", "this morning", "last week", "recent",
    "morning briefing", "what did we do", "this session", "just now",
    "a minute ago", "earlier today", "already", "we just",
])
_TOOLS_KW = frozenset([
    "tool", "install", "configure", "/tools", "setup", "auth_google",
    "auth_github", "integration", "what can you", "available", "capability",
    "github", "google drive", "calendar", "gmail",
])
_AGENTS_KW = frozenset([
    "agent", "sub-agent", "delegate", "/agents", "specialist",
    "create agent", "new agent", "sub agent",
])
_HEARTBEAT_KW = frozenset([
    "heartbeat", "health", "disk", "cpu", "ram", "server",
    "/health", "/status", "monitoring", "alert", "threshold",
    "morning briefing", "full report", "quick check",
])
_DB_KW = frozenset([
    "database", "db", "query", "table", "track", "stats",
    "log history", "show me all", "how many", "sql",
    "heartbeat_log", "permission_log", "conversation_stats",
    "/db", "structured", "stored memories",
])
_PERMISSIONS_KW = frozenset([
    "permission", "approve", "deny", "sandbox", "/permissions",
    "allowlist", "blocked", "allow list",
])
_STORAGE_KW = frozenset([
    "storage", "purge", "cleanup", "disk full", "free space",
    "tier", "old files", "/purge", "/storage",
])


class KovoAgent:
    """Main agent — single entry point for all owner requests."""

    name = "kovo"

    def __init__(
        self,
        memory: "MemoryManager",
        router: "ModelRouter",
        skills: "SkillRegistry",
        tool_registry: "ToolRegistry",
        sub_agent_runner: "SubAgentRunner | None" = None,
        structured_store=None,  # StructuredStore — optional, avoids circular import
    ):
        self.memory = memory
        self.router = router
        self.skills = skills
        self.tool_registry = tool_registry
        self.sub_agent_runner = sub_agent_runner
        self.store = structured_store

        # user_id → claude session_id
        self._sessions: dict[int, str] = {}
        # user_id → topic Counter
        self._topic_counts: dict[int, Counter] = {}
        # topics already recommended to user (don't spam)
        self._recommended: set[str] = set()

        # Optional phone/TTS/transcription (wired up by gateway)
        self.tts = None
        self.caller = None
        self.tg_bot = None
        self.owner_user_id: int | None = None
        self.transcriber = None   # set by gateway if Groq/Whisper available

    # ── System prompt ─────────────────────────────────────────────────────

    def build_system_prompt(self, user_message: str = "") -> str:
        """
        Build a context-aware system prompt using keyword-based on-demand loading.
        Always loads: SOUL.md, USER.md (~200 tokens).
        Loads on demand only when message keywords match:
          MEMORY.md, daily logs, best-matching skill, TOOLS.md, AGENTS.md,
          HEARTBEAT.md, DB schema, permissions info, storage info.
        Fallback: if nothing was conditionally loaded, adds MEMORY.md + TOOLS.md
          as a safety net for ambiguous messages.
        """
        msg = user_message.lower()
        parts: list[str] = []
        conditional_loaded = 0  # tracks how many optional sections were added

        # ── Always: core identity files (~300 tokens) ─────────────────────
        soul = self.memory.soul()
        if soul:
            parts.append(soul)

        user_profile = self.memory.user_profile()
        if user_profile:
            parts.append(user_profile)

        # ── Always: pinned memory (core facts about the owner) ──────────
        pinned = self.memory.pinned_memory()
        if pinned:
            parts.append(f"## Key Facts\n{pinned}")

        # ── Conditional: learnings (rolling log) ─────────────────────────
        if self._needs_memory(msg):
            learnings = self.memory.learnings_memory()
            if learnings:
                parts.append(f"## Learnings\n{learnings[-3000:]}")
                conditional_loaded += 1

        # ── Conditional: daily logs ────────────────────────────────────────
        if self._needs_daily_logs(msg):
            today_log = self.memory.daily_log()
            if today_log:
                parts.append(f"## Today's Activity\n{today_log[-3000:]}")
                conditional_loaded += 1
            yesterday_log = self.memory.daily_log(_tz_today() - timedelta(days=1))
            if yesterday_log and ("yesterday" in msg or "last week" in msg):
                parts.append(f"## Yesterday's Activity\n{yesterday_log[-1500:]}")

        # ── Conditional: best-matching skill only ─────────────────────────
        skill = self._find_matching_skill(user_message)
        if skill:
            parts.append(skill.system_prompt_block)
            conditional_loaded += 1

        # ── Conditional: HEARTBEAT.md ─────────────────────────────────────
        if self._needs_heartbeat(msg):
            hb = self.memory.heartbeat()
            if hb:
                parts.append(f"## Heartbeat Configuration\n{hb}")
                conditional_loaded += 1

        # ── Conditional: tool registry ────────────────────────────────────
        if self._needs_tools(msg):
            tools_block = self.tool_registry.as_system_prompt_block()
            if tools_block:
                parts.append(tools_block)
                conditional_loaded += 1

        # ── Conditional: sub-agents ───────────────────────────────────────
        if self._needs_agents(msg) and self.sub_agent_runner:
            agents_block = self.sub_agent_runner.as_system_prompt_block()
            if agents_block:
                parts.append(agents_block)
                conditional_loaded += 1

        # ── Conditional: DB schema ────────────────────────────────────────
        if self._needs_db_schema(msg) and self.store:
            schema = self.store.get_schema()
            parts.append(f"## Structured Database Schema\n{schema}")
            conditional_loaded += 1

        # ── Conditional: permissions info ─────────────────────────────────
        if self._needs_permissions(msg):
            parts.append(
                "## Permissions System\n"
                "Use `/permissions` to view the Claude Code sandbox allowlist.\n"
                "Use `/approve` or `/deny` to grant/reject pending permission requests.\n"
                "All approve/deny events are logged to the `permission_log` SQLite table."
            )
            conditional_loaded += 1

        # ── Conditional: storage tier info ────────────────────────────────
        if self._needs_storage(msg):
            parts.append(
                "## Storage Management\n"
                "Tier 1 (auto-purge, no approval): data/tmp/ (1 day), data/audio/ (7 days), data/screenshots/ (7 days)\n"
                "Tier 2 (ask first): data/photos/ (30 days), data/documents/ (30 days), data/images/ (30 days)\n"
                "Commands: /storage (disk report), /purge all|photos|documents|images"
            )
            conditional_loaded += 1

        # ── Fallback: ambiguous message — load MEMORY.md + TOOLS.md ───────
        if conditional_loaded == 0:
            learnings = self.memory.learnings_memory()
            if learnings:
                parts.append(f"## Recent Learnings\n{learnings[-2000:]}")
            tools_block = self.tool_registry.as_system_prompt_block()
            if tools_block:
                parts.append(tools_block)

        # ── Always: image sending capability ─────────────────────────────
        parts.append(
            "## Image Sending\n"
            "You can send images directly to the owner in Telegram.\n"
            "To send an image, include `[SEND_IMAGE: your search query]` anywhere in your response.\n"
            "Example: `[SEND_IMAGE: cat playing piano]`\n"
            "The bot will search for the image, download it, and send it as a photo.\n"
            "You can include one or more image tags per response.\n"
            "Use this whenever the owner asks to see a photo, image, picture, or visual."
        )

        return "\n\n---\n\n".join(parts)

    # ── Keyword classifiers (pure Python, zero cost) ──────────────────────

    def _needs_memory(self, msg: str) -> bool:
        return any(kw in msg for kw in _MEMORY_KW)

    def _needs_daily_logs(self, msg: str) -> bool:
        return any(kw in msg for kw in _LOG_KW)

    def _needs_tools(self, msg: str) -> bool:
        return any(kw in msg for kw in _TOOLS_KW)

    def _needs_agents(self, msg: str) -> bool:
        return any(kw in msg for kw in _AGENTS_KW)

    def _needs_heartbeat(self, msg: str) -> bool:
        return any(kw in msg for kw in _HEARTBEAT_KW)

    def _needs_db_schema(self, msg: str) -> bool:
        return any(kw in msg for kw in _DB_KW)

    def _needs_permissions(self, msg: str) -> bool:
        return any(kw in msg for kw in _PERMISSIONS_KW)

    def _needs_storage(self, msg: str) -> bool:
        return any(kw in msg for kw in _STORAGE_KW)

    def _find_matching_skill(self, message: str):
        """Return the single best-matching skill, or None."""
        return self.skills.match_best(message)

    # ── Core handle ───────────────────────────────────────────────────────

    async def handle(
        self,
        message: str,
        user_id: int = 0,
        force_complexity: str | None = None,
        files: list[str] | None = None,
    ) -> dict:
        session_id = self._sessions.get(user_id)
        system_prompt = self.build_system_prompt(message)

        # Sub-agent delegation is text-only (files stay with the main agent)
        if self.sub_agent_runner and not files:
            sub_result = await self.sub_agent_runner.maybe_delegate(
                message, session_id, system_prompt, force_complexity
            )
            if sub_result:
                self._persist(user_id, message, sub_result)
                return sub_result

        result = await self.router.route(
            message,
            system_prompt=system_prompt,
            session_id=session_id,
            force_complexity=force_complexity,
            files=files,
        )
        result["agent"] = self.name

        new_session = result.get("session_id")
        if new_session:
            self._sessions[user_id] = new_session

        self._persist(user_id, message, result)
        self._track_topics(user_id, message)

        # Append sub-agent recommendation if threshold hit
        rec, rec_topic = self._maybe_recommend_sub_agent(user_id)
        if rec:
            result["text"] = result["text"] + f"\n\n---\n{rec}"
            result["__sub_agent_topic__"] = rec_topic

        return result

    # ── Vision ────────────────────────────────────────────────────────────

    async def handle_image(
        self,
        image_path: str,
        prompt: str,
        user_id: int = 0,
    ) -> dict:
        """
        Analyze an image via the Anthropic Messages API (vision).
        Builds the full system prompt and persists the exchange to daily memory.
        """
        from src.tools.vision import analyze_image
        system_prompt = self.build_system_prompt(prompt)
        try:
            text = await analyze_image(
                image_path=image_path,
                prompt=prompt,
                system_prompt=system_prompt,
            )
            result = {"text": text, "model_used": "claude/opus", "agent": self.name}
        except Exception as e:
            log.error("Image analysis failed: %s", e)
            result = {
                "text": f"Sorry, image analysis failed: {e}",
                "model_used": "error",
                "agent": self.name,
            }
        self._persist(user_id, f"[image] {prompt}", result)
        return result

    # ── TTS / call (wired up by gateway) ─────────────────────────────────

    async def make_call(self, message: str, urgent: bool = False) -> dict:
        if self.tts is None or self.caller is None:
            return {"text": "Phone tool not configured. Check TOOLS.md.", "method": "error"}
        try:
            prefix = "Urgent message from Kovo: " if urgent else ""
            mp3_path = await self.tts.speak(
                prefix + message,
                output_path=str(data_path() / "audio" / "call_audio.mp3"),
            )
        except Exception as e:
            log.error("TTS failed: %s", e)
            return {"text": f"TTS failed: {e}", "method": "error"}

        try:
            result = await self.caller.call_user(
                user_id=self.owner_user_id,
                audio_path=mp3_path,
                tg_bot=self.tg_bot,
                bot_chat_id=self.owner_user_id,
            )
            method = result.get("method", "unknown")
            emoji = "📞" if method == "call" else "🎤"
            return {"text": f"{emoji} Delivered via {method}.", "model_used": "tts", "method": method}
        except Exception as e:
            log.error("Call delivery failed: %s", e)
            return {"text": f"Call failed: {e}", "method": "error"}

    # ── Session management ────────────────────────────────────────────────

    def clear_session(self, user_id: int) -> None:
        self._sessions.pop(user_id, None)

    def get_session(self, user_id: int) -> str | None:
        return self._sessions.get(user_id)

    # ── Internal helpers ──────────────────────────────────────────────────

    def _persist(self, user_id: int, message: str, result: dict) -> None:
        timestamp = datetime.now(_get_configured_tz()).strftime("%H:%M")
        model_used = result.get("model_used", "?")
        agent_used = result.get("agent", self.name)
        entry = (
            f"- [{timestamp}] agent={agent_used} model={model_used}\n"
            f"  User: {message[:300]}\n"
            f"  Reply: {result.get('text', '')[:500]}"
        )
        self.memory.append_daily_log(entry, session_label=f"Session {timestamp}")

    def _track_topics(self, user_id: int, message: str) -> None:
        msg_lower = message.lower()
        counter = self._topic_counts.setdefault(user_id, Counter())
        for topic, keywords in _TOPIC_KEYWORDS.items():
            if any(kw in msg_lower for kw in keywords):
                counter[topic] += 1

    def _maybe_recommend_sub_agent(self, user_id: int) -> tuple[str | None, str | None]:
        """Return (recommendation_text, topic) or (None, None)."""
        counter = self._topic_counts.get(user_id)
        if not counter:
            return None, None
        for topic, count in counter.items():
            if count >= _PATTERN_THRESHOLD and topic not in self._recommended:
                self._recommended.add(topic)
                text = (
                    f"💡 I've noticed you ask a lot of **{topic.replace('_', ' ')}** questions. "
                    f"Want me to create a dedicated **{topic}** sub-agent with specialised skills?"
                )
                return text, topic
        return None, None
