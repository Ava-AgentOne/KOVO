"""
ClaudeAgentSDKBrain — Claude via the Claude Agent SDK.

Replaces the `claude -p` subprocess (Phase 3a) with the official SDK:
structured messages instead of stdout parsing, native session resume, and
the foundation for streaming (3b), custom tools (3c), and MCP (3d). Auth
is unchanged — the same CLAUDE_CODE_OAUTH_TOKEN / Max subscription the
CLI uses.

The response dict matches the CLI JSON shape so callers can't tell the
difference; errors raise ClaudeCLIError just like the subprocess path.
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import logging

from src.brains.base import Brain
from src.utils.platform import kovo_dir

log = logging.getLogger(__name__)


class ClaudeAgentSDKBrain(Brain):
    name = "claude-sdk"
    supports_streaming = True

    def generate(
        self,
        prompt: str,
        session_id: str | None = None,
        model: str | None = None,
        system_prompt: str | None = None,
        timeout: int = 600,
        files: list[str] | None = None,
    ) -> dict:
        coro = self._generate(prompt, session_id, model, system_prompt, timeout, files)
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)
        # Defensive: called from inside an event loop (callers normally use
        # run_in_executor). Run in a private thread instead of deadlocking.
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()

    async def generate_stream(
        self,
        prompt: str,
        session_id: str | None = None,
        model: str | None = None,
        system_prompt: str | None = None,
        timeout: int = 600,
        files: list[str] | None = None,
        on_delta=None,
    ) -> dict:
        return await self._generate(
            prompt, session_id, model, system_prompt, timeout, files, on_delta=on_delta
        )

    async def _generate(self, prompt, session_id, model, system_prompt, timeout, files, on_delta=None) -> dict:
        from claude_agent_sdk import (
            AssistantMessage,
            ClaudeAgentOptions,
            ResultMessage,
            StreamEvent,
            TextBlock,
            query,
        )
        from src.tools.claude_cli import ClaudeCLIError, _detect_permission_error

        if files:
            # No --file equivalent in the SDK; Claude Code reads local paths
            # itself, so reference them in the prompt (vision.py parity).
            prompt = prompt + "\n\nFiles to examine:\n" + "\n".join(f"- {f}" for f in files)

        options = ClaudeAgentOptions(
            model=model,
            system_prompt=system_prompt,
            resume=session_id,
            permission_mode="acceptEdits",
            cwd=str(kovo_dir()),
            # Load /opt/kovo/.claude settings — same allowlist the CLI used
            setting_sources=["project", "local"],
            include_partial_messages=bool(on_delta),
        )

        text_parts: list[str] = []
        result: dict = {}
        preview_parts: list[str] = []

        async def _run():
            async for msg in query(prompt=prompt, options=options):
                if isinstance(msg, StreamEvent):
                    # Raw Anthropic stream event — text deltas feed the live
                    # preview only; the authoritative text still comes from
                    # the complete messages below.
                    if on_delta is not None:
                        ev = msg.event or {}
                        delta = ev.get("delta") or {}
                        if ev.get("type") == "content_block_delta" and delta.get("type") == "text_delta":
                            preview_parts.append(delta.get("text", ""))
                            try:
                                await on_delta("".join(preview_parts))
                            except Exception as cb_err:
                                log.debug("on_delta callback error: %s", cb_err)
                elif isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        if isinstance(block, TextBlock):
                            text_parts.append(block.text)
                elif isinstance(msg, ResultMessage):
                    result.update(
                        session_id=msg.session_id,
                        total_cost_usd=msg.total_cost_usd,
                        is_error=msg.is_error,
                        num_turns=msg.num_turns,
                        usage=msg.usage,
                    )
                    if getattr(msg, "result", None):
                        result["result"] = msg.result

        try:
            await asyncio.wait_for(_run(), timeout=timeout)
        except asyncio.TimeoutError as e:
            raise ClaudeCLIError(f"claude SDK call timed out after {timeout}s") from e
        except Exception as e:
            # SDK raises on error results (e.g. auth failures, blocked
            # commands surfaced as errors). Keep CLI-compatible behavior.
            perm = _detect_permission_error(str(e))
            if perm:
                return self._permission_sentinel(perm, "", session_id)
            raise ClaudeCLIError(f"claude SDK error: {e}") from e

        text = result.get("result") or "".join(text_parts)

        # Exit-0 permission block embedded in the reply text (CLI parity)
        perm = _detect_permission_error(text or "")
        if perm:
            return self._permission_sentinel(perm, text, result.get("session_id"))

        result["result"] = text
        return result

    @staticmethod
    def _permission_sentinel(pattern: str, text: str, session_id: str | None) -> dict:
        blocked_cmd = pattern[5:].rstrip(" *)").strip()
        log.warning("Permission error detected (SDK) — pattern=%s", pattern)
        return {
            "__permission_needed__": True,
            "pattern": pattern,
            "blocked_command": blocked_cmd,
            "result": text,
            "session_id": session_id,
        }
