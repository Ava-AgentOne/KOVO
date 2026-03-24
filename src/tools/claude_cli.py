"""
Claude Code CLI subprocess wrapper.
Calls `claude -p` with the given prompt and returns the parsed response.
"""
import json
import logging
import re
import signal
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Set when our own process receives SIGTERM — used to skip the 143 retry
# so a shutdown isn't delayed by a second full claude invocation.
_shutting_down = False


def _on_sigterm(signum, frame):
    global _shutting_down
    _shutting_down = True
    # Re-raise so the existing handlers (uvicorn etc.) still fire.
    signal.signal(signal.SIGTERM, signal.SIG_DFL)
    signal.raise_signal(signal.SIGTERM)


signal.signal(signal.SIGTERM, _on_sigterm)

log = logging.getLogger(__name__)

_SETTINGS_FILE = Path("/opt/kovo/.claude/settings.local.json")
_MEMORY_DIR = Path("/opt/kovo/workspace/memory")
_DUBAI_TZ = timezone(timedelta(hours=4))

# Optional StructuredStore reference — set by gateway after init
_structured_store = None

# Patterns Claude Code uses when a Bash command is blocked by the allowlist
_PERM_ERR_PATTERNS = [
    # Claude Code's canonical format in error output: "Bash(docker *)"
    re.compile(r'Bash\((\w[\w.-]*)', re.IGNORECASE),
    # "not allowed: docker" / "permission denied: docker"
    re.compile(r'(?:not allowed|permission denied|not permitted)[:\s]+`?(\w[\w.-]*)', re.IGNORECASE),
    # "`docker` is not in the allowlist" / "`docker` is blocked"
    re.compile(r'`(\w[\w.-]+)`\s+is\s+(?:not\s+(?:in|allowed)|blocked)', re.IGNORECASE),
]

# Words that look like commands but aren't — filter false positives
_PERM_NOISE = frozenset({
    'the', 'a', 'an', 'this', 'that', 'bash', 'command',
    'shell', 'tool', 'use', 'by', 'run', 'it',
})


class ClaudeCLIError(Exception):
    pass


def _detect_permission_error(text: str) -> str | None:
    """
    Scan Claude Code output for a blocked-command error.
    Returns a permission pattern like "Bash(docker *)", or None if not a permission error.
    """
    for pattern in _PERM_ERR_PATTERNS:
        m = pattern.search(text)
        if m:
            cmd = m.group(1).strip().lower().rstrip("*)(")
            if cmd and cmd not in _PERM_NOISE and len(cmd) > 1:
                return f"Bash({cmd} *)"
    return None


def _log_permission_grant(pattern: str) -> None:
    """Append a permission-grant event to today's daily log."""
    try:
        today = datetime.now(_DUBAI_TZ).strftime("%Y-%m-%d")
        timestamp = datetime.now(_DUBAI_TZ).strftime("%H:%M")
        log_file = _MEMORY_DIR / f"{today}.md"
        entry = f"\n- [{timestamp}] 🔑 Permission granted by Esam: `{pattern}`\n"
        with open(log_file, "a") as f:
            f.write(entry)
    except Exception as e:
        log.warning("Failed to write permission grant to daily log: %s", e)


def add_permission(pattern: str) -> bool:
    """
    Add a Bash permission pattern to .claude/settings.local.json.
    Keeps the allow list sorted. Returns True on success.
    """
    try:
        data = json.loads(_SETTINGS_FILE.read_text())
        allow: list = data.setdefault("permissions", {}).setdefault("allow", [])
        if pattern in allow:
            log.info("Permission already present: %s", pattern)
            return True
        allow.append(pattern)
        allow.sort()
        _SETTINGS_FILE.write_text(json.dumps(data, indent=2) + "\n")
        log.info("Permission added: %s (%d total)", pattern, len(allow))
        _log_permission_grant(pattern)
        if _structured_store is not None:
            cmd = pattern[5:].rstrip(" *)").strip() if pattern.startswith("Bash(") else None
            _structured_store.log_permission("approve", pattern, cmd)
        return True
    except Exception as e:
        log.error("Failed to add permission %s: %s", pattern, e)
        return False


def deny_permission(pattern: str) -> None:
    """Log a permission denial to SQLite (called when user replies /deny)."""
    if _structured_store is not None:
        cmd = pattern[5:].rstrip(" *)").strip() if pattern.startswith("Bash(") else None
        _structured_store.log_permission("deny", pattern, cmd)
    log.info("Permission denied: %s", pattern)


def get_permissions() -> list[str]:
    """Return the current allow list from .claude/settings.local.json."""
    try:
        data = json.loads(_SETTINGS_FILE.read_text())
        return data.get("permissions", {}).get("allow", [])
    except Exception as e:
        log.error("Failed to read permissions: %s", e)
        return []


def call_claude(
    prompt: str,
    session_id: str | None = None,
    model: str | None = None,
    system_prompt: str | None = None,
    timeout: int = 600,
    files: list[str] | None = None,
) -> dict:
    """
    Synchronous wrapper around `claude -p`.
    Returns the parsed JSON response dict (keys: result, session_id, cost_usd, etc.).
    Exit code 143 (SIGTERM) is retried once automatically before raising.
    files: local file paths attached via --file (images, PDFs, etc. for Claude vision/analysis).

    If a command is blocked by the sandbox, returns a special dict:
      {"__permission_needed__": True, "pattern": "Bash(cmd *)", "blocked_command": "cmd", ...}
    instead of raising, so the caller can ask the user for approval.
    """
    cmd = ["claude", "-p", prompt, "--output-format", "json", "--permission-mode", "acceptEdits"]
    if session_id:
        cmd.extend(["--resume", session_id])
    if model:
        cmd.extend(["--model", model])
    if system_prompt:
        cmd.extend(["--system-prompt", system_prompt])
    for f in (files or []):
        cmd.extend(["--file", f])

    log.debug("claude cmd: %s", " ".join(cmd[:4]) + " ...")

    def _run() -> subprocess.CompletedProcess:
        try:
            return subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as e:
            raise ClaudeCLIError(f"claude -p timed out after {timeout}s") from e

    result = _run()

    # Exit code 143 = SIGTERM (process was killed, often transiently).
    # Only retry if we ourselves are NOT shutting down — otherwise the retry
    # would block the service from stopping cleanly.
    if result.returncode == 143 and not _shutting_down:
        log.warning("claude -p exited 143 (SIGTERM) — retrying once")
        result = _run()

    if result.returncode != 0:
        # Check stderr for a permission error before raising
        perm_pattern = _detect_permission_error(result.stderr)
        if perm_pattern:
            blocked_cmd = perm_pattern[5:].rstrip(" *)").strip()
            log.warning("Permission error detected — pattern=%s stderr=%s", perm_pattern, result.stderr[:200])
            return {
                "__permission_needed__": True,
                "pattern": perm_pattern,
                "blocked_command": blocked_cmd,
                "result": "",
                "session_id": None,
            }
        raise ClaudeCLIError(
            f"claude -p exited {result.returncode}: {result.stderr[:500]}"
        )

    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise ClaudeCLIError(
            f"claude -p returned non-JSON (exit {result.returncode}): {result.stdout[:200]}"
        ) from e

    # Also check the result text for permission errors (exit-0 case where
    # Claude Code embeds the blocked-command notice in its own reply).
    result_text = str(parsed.get("result", ""))
    perm_pattern = _detect_permission_error(result_text)
    if perm_pattern:
        blocked_cmd = perm_pattern[5:].rstrip(" *)").strip()
        log.warning("Permission error in result text — pattern=%s", perm_pattern)
        return {
            "__permission_needed__": True,
            "pattern": perm_pattern,
            "blocked_command": blocked_cmd,
            "result": result_text,
            "session_id": parsed.get("session_id"),
        }

    return parsed


def extract_text(response: dict) -> str:
    """Pull the assistant text out of a claude -p JSON response."""
    # Newer claude CLI: response["result"] is the text
    if "result" in response:
        return str(response["result"])
    # Fallback: look inside content blocks
    for block in response.get("content", []):
        if isinstance(block, dict) and block.get("type") == "text":
            return block["text"]
    return str(response)
