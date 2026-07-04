"""
Model router:
  simple   → Claude Sonnet  (fast, cheap, conversational)
  medium   → Claude Sonnet  (default for most tasks)
  complex  → Claude Opus    (auto-escalate: code, debugging, design, research, planning)

Classification is instant keyword-only (no API calls, no Ollama).
Ollama is used exclusively by the heartbeat scheduler for health summaries.
"""
import asyncio
import logging
from functools import partial

from src.gateway import config as cfg
from src.router.classifier import MessageClassifier
from src.tools.claude_cli import ClaudeCLIError, call_claude, extract_text

log = logging.getLogger(__name__)


class ModelRouter:
    def __init__(self, classifier: MessageClassifier = None):
        self.classifier = classifier

    async def route(
        self,
        message: str,
        system_prompt: str | None = None,
        session_id: str | None = None,
        force_complexity: str | None = None,
        files: list[str] | None = None,
        on_delta=None,
    ) -> dict:
        """
        Route the message to the right Claude model.
        Returns {"text": str, "model_used": str, "complexity": str, "session_id": str|None}.
        files: optional file paths attached via --file (images, PDFs, etc.).
        on_delta: optional async callback awaited with the accumulated reply
        text while it is being generated (streaming brains only — silently
        ignored when the active brain can't stream).
        """
        if force_complexity:
            complexity = force_complexity
            log.info("Routing: forced complexity=%s", complexity)
        else:
            classification = await self.classifier.classify(message)
            complexity = classification["complexity"]
            log.info("Routing: classified complexity=%s", complexity)

        # simple + medium → Sonnet, complex → Opus
        model = "opus" if complexity == "complex" else "sonnet"

        try:
            response = await self._call_model(
                message, model, system_prompt, session_id, files, on_delta
            )

            # Propagate permission-needed signal up to the bot layer
            if response.get("__permission_needed__"):
                return {
                    "__permission_needed__": True,
                    "pattern": response["pattern"],
                    "blocked_command": response.get("blocked_command", ""),
                    "text": "",
                    "model_used": "blocked",
                    "complexity": complexity,
                    "session_id": session_id,
                }

            text = extract_text(response)
            new_session = response.get("session_id") or session_id
            return {
                "text": text,
                "model_used": f"claude/{model}",
                "complexity": complexity,
                "session_id": new_session,
            }
        except ClaudeCLIError as e:
            log.error("Claude CLI error: %s", e)
            return {
                "text": f"Sorry, I ran into an error: {e}",
                "model_used": "error",
                "complexity": complexity,
                "session_id": session_id,
            }

    async def _call_model(self, message, model, system_prompt, session_id, files, on_delta) -> dict:
        """Streaming path when the active brain supports it, else executor + call_claude."""
        if on_delta is not None:
            from src.brains import get_claude_brain
            brain = get_claude_brain()
            if brain is not None and brain.supports_streaming:
                return await brain.generate_stream(
                    message,
                    session_id=session_id,
                    model=model,
                    system_prompt=system_prompt,
                    timeout=cfg.claude_timeout(),
                    files=files,
                    on_delta=on_delta,
                )

        loop = asyncio.get_event_loop()
        fn = partial(
            call_claude,
            message,
            session_id=session_id,
            model=model,
            system_prompt=system_prompt,
            timeout=cfg.claude_timeout(),
            files=files,
        )
        return await loop.run_in_executor(None, fn)
