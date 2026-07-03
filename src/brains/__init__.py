"""
Brain factory — selects the AI backend from settings.yaml.

    brains:
      claude: sdk    # Claude Agent SDK (in-process)
      # claude: cli  # claude -p subprocess (default, historical path)

get_claude_brain() returns the active non-CLI brain, or None to signal
that call_claude() should use its original subprocess path. Falls back
to the CLI automatically if the SDK isn't importable, so a bad config
can never take KOVO's brain offline.
"""
from __future__ import annotations

import logging

log = logging.getLogger(__name__)

_sdk_brain = None


def claude_backend() -> str:
    """Configured Claude backend: 'cli' (default) or 'sdk'."""
    try:
        from src.gateway import config as cfg
        return str(cfg.get().get("brains", {}).get("claude", "cli")).strip().lower()
    except Exception:
        return "cli"


def get_claude_brain():
    """Return the active Brain for Claude calls, or None for the CLI path."""
    global _sdk_brain
    if claude_backend() != "sdk":
        return None
    if _sdk_brain is None:
        try:
            from src.brains.claude_sdk import ClaudeAgentSDKBrain
            _sdk_brain = ClaudeAgentSDKBrain()
            log.info("Claude brain: Agent SDK")
        except Exception as e:
            log.error("Claude SDK brain unavailable (%s) — falling back to CLI", e)
            return None
    return _sdk_brain
