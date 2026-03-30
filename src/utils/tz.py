"""Shared timezone helper — reads from settings.yaml."""
from datetime import date, datetime, timezone, timedelta
import sys

_tz_cache = None


def get_tz():
    """Return a timezone object for the configured timezone.
    Uses zoneinfo (Python 3.9+) for DST-aware timezones.
    Falls back to fixed offsets for UTC+N format or if zoneinfo unavailable.
    """
    global _tz_cache
    if _tz_cache is not None:
        return _tz_cache
    tz_name = "UTC"
    try:
        from src.gateway.config import kovo_timezone
        tz_name = kovo_timezone()
    except Exception:
        pass
    _tz_cache = _parse_tz(tz_name)
    return _tz_cache


def _parse_tz(name: str):
    """Parse a timezone name into a timezone object.
    Tries zoneinfo first (DST-aware), falls back to fixed offset.
    """
    # Try zoneinfo (Python 3.9+) — handles DST correctly
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(name)
    except (ImportError, KeyError):
        pass

    # Fallback: UTC+N format
    if name.startswith("UTC"):
        try:
            offset = name[3:].replace(" ", "")
            if offset:
                return timezone(timedelta(hours=float(offset)))
            return timezone.utc
        except (ValueError, IndexError):
            pass

    return timezone.utc


def reset_cache() -> None:
    """Clear cached timezone — called when settings change."""
    global _tz_cache
    _tz_cache = None


def now() -> datetime:
    return datetime.now(get_tz())


def today() -> date:
    return now().date()
