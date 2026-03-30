"""
Configuration loader — reads settings.yaml + .env and exposes a Settings object.
Also provides: TokenMaskFilter (logging), EnvValidationError, validate_env().
"""
import logging
import os
import stat
from pathlib import Path
import yaml
from dotenv import load_dotenv

_BASE = Path(__file__).resolve().parents[2]  # resolves to kovo_dir()
_ENV_FILE = _BASE / "config" / ".env"
_SETTINGS_FILE = _BASE / "config" / "settings.yaml"

load_dotenv(_ENV_FILE)


# ── Logging filter — masks secrets in log records ─────────────────────────────

_SENSITIVE_VARS = [
    "TELEGRAM_BOT_TOKEN",
    "GROQ_API_KEY",
    "GITHUB_TOKEN",
    "CLAUDE_CODE_OAUTH_TOKEN",
    "TELEGRAM_API_HASH",
]


class TokenMaskFilter(logging.Filter):
    """Replace secret env var values with ***REDACTED*** in every log record."""

    def __init__(self):
        super().__init__()
        self._secrets: list[str] = []
        for var in _SENSITIVE_VARS:
            val = os.environ.get(var, "").strip()
            if val and not val.startswith("your_"):
                self._secrets.append(val)

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003
        if self._secrets:
            msg = record.getMessage()
            for secret in self._secrets:
                msg = msg.replace(secret, "***REDACTED***")
            record.msg = msg
            record.args = ()
        return True


# ── Startup environment validation ────────────────────────────────────────────

_REQUIRED_VARS = ["TELEGRAM_BOT_TOKEN", "OWNER_TELEGRAM_ID"]
_RECOMMENDED_VARS = ["CLAUDE_CODE_OAUTH_TOKEN"]


class EnvValidationError(Exception):
    pass


def validate_env() -> None:
    """
    Check that required env vars are set and not placeholder values.
    Raises EnvValidationError listing all problems + fix command.
    """
    problems: list[str] = []
    for var in _REQUIRED_VARS:
        val = os.environ.get(var, "").strip()
        if not val:
            problems.append(f"  missing: {var}")
        elif val.startswith("your_"):
            problems.append(f"  placeholder not replaced: {var}={val!r}")

    warnings: list[str] = []
    for var in _RECOMMENDED_VARS:
        val = os.environ.get(var, "").strip()
        if not val or val.startswith("your_"):
            warnings.append(f"  recommended but not set: {var}")

    if warnings:
        _warn_log = logging.getLogger(__name__)
        for w in warnings:
            _warn_log.warning("env: %s", w.strip())

    if problems:
        msg = (
            "Kovo startup aborted — fix your config/.env file:\n"
            + "\n".join(problems)
            + "\n\nRun:  nano " + str(_ENV_FILE) + ""
        )
        raise EnvValidationError(msg)


def check_env_permissions() -> None:
    """Warn if .env is group- or world-readable."""
    if not _ENV_FILE.exists():
        return
    mode = _ENV_FILE.stat().st_mode
    if mode & (stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH):
        logging.getLogger(__name__).warning(
            ".env file has loose permissions (%s) — run: chmod 600 %s",
            oct(mode & 0o777),
            _ENV_FILE,
        )


def _expand(value):
    """Recursively expand ${VAR} references in yaml values."""
    if isinstance(value, str):
        import re
        return re.sub(r"\$\{(\w+)\}", lambda m: os.environ.get(m.group(1), ""), value)
    if isinstance(value, dict):
        return {k: _expand(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand(i) for i in value]
    return value


def _load() -> dict:
    with open(_SETTINGS_FILE) as f:
        raw = yaml.safe_load(f)
    return _expand(raw)


_cfg: dict | None = None


def reload() -> None:
    """Invalidate the cached config — next get() will re-read settings.yaml."""
    global _cfg
    _cfg = None
    try:
        from src.utils.tz import reset_cache
        reset_cache()
    except Exception:
        pass


def get() -> dict:
    global _cfg
    if _cfg is None:
        _cfg = _load()
    return _cfg


# --- Convenience accessors ---

def telegram_token() -> str:
    return get()["telegram"]["token"]


def allowed_users() -> list[int]:
    return [int(u) for u in get()["telegram"]["allowed_users"]]


def ollama_url() -> str:
    return get()["ollama"]["url"]


def ollama_default_model() -> str:
    return get()["ollama"]["default_model"]


def claude_default_model() -> str:
    return get()["claude"]["default_model"]


def claude_timeout() -> int:
    return int(get()["claude"]["timeout"])


def workspace_dir() -> Path:
    return Path(get()["kovo"]["workspace"])


def data_dir() -> Path:
    return Path(get()["kovo"]["data_dir"])


def log_dir() -> Path:
    return Path(get()["kovo"]["log_dir"])


def gateway_host() -> str:
    return get()["gateway"]["host"]


def gateway_port() -> int:
    return int(get()["gateway"]["port"])


def kovo_timezone() -> str:
    """Return configured timezone (e.g. Asia/Dubai). Default: UTC."""
    return get().get("kovo", {}).get("timezone", "UTC")
