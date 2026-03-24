"""
Keyword-only message complexity classifier.
Returns: {"complexity": "simple|medium|complex"}

Routing rules:
  simple/medium → Claude Sonnet  (fast, conversational)
  complex       → Claude Opus    (auto-escalate: code, debugging, planning, research…)

No API calls are made here. Classification is instant keyword screening only.
Ambiguous messages default to Sonnet ("medium") — Opus is only used when a
clear complex trigger is found.
"""
import logging
import re

log = logging.getLogger(__name__)


class MessageClassifier:
    def __init__(self, claude_client=None, model: str = "claude-sonnet-4-6"):
        # Parameters kept for API compatibility — classification is keyword-only.
        pass

    async def classify(self, message: str) -> dict:
        """
        Returns {"complexity": "simple"|"medium"|"complex"}.
        Instant keyword screening — no API calls, no network dependency.
        """
        complexity = _keyword_classify(message)
        log.debug("Keyword classification: %s for %r", complexity, message[:60])
        return {"complexity": complexity}


# ── Keyword sets ──────────────────────────────────────────────────────────────

_COMPLEX_KEYWORDS = {
    # Programming / code
    "code", "coding", "program", "programming", "script", "scripting",
    "function", "class", "method", "algorithm", "implement", "implementation",
    "refactor", "debug", "debugging", "bug", "fix the", "error in",
    # Languages / web
    "python", "javascript", "typescript", "html", "css", "sql", "bash",
    "react", "vue", "angular", "node", "django", "fastapi", "flask",
    "api", "endpoint", "database", "schema", "query",
    # Design / content
    "web design", "ui design", "ux design", "content design", "layout",
    "stylesheet", "template", "component",
    # Reasoning / planning
    "plan", "planning", "architecture", "design the", "research",
    "analyze", "analyse", "deep dive", "investigate", "compare",
    "multi-step", "step by step", "walk me through",
}

_SIMPLE_KEYWORDS = {
    "hi", "hello", "hey", "thanks", "thank you", "ok", "okay", "yes", "no",
    "what time", "what day", "what date", "remind me", "status", "ping",
    "how are you", "what's up", "sup",
}


def _keyword_classify(message: str) -> str:
    """
    Returns "simple", "medium", or "complex".
    Never returns None — ambiguous messages default to "medium" (Sonnet).
    """
    lower = message.lower().strip()

    # Complex triggers — checked first (takes priority over simple)
    for kw in _COMPLEX_KEYWORDS:
        if " " in kw:
            if kw in lower:
                return "complex"
        else:
            if re.search(rf"\b{re.escape(kw)}\b", lower):
                return "complex"

    # Simple triggers — short greetings, status checks, etc.
    if len(lower) < 60:
        for kw in _SIMPLE_KEYWORDS:
            if " " in kw:
                if kw in lower:
                    return "simple"
            else:
                if re.search(rf"\b{re.escape(kw)}\b", lower):
                    return "simple"

    # Everything else → Sonnet
    return "medium"
