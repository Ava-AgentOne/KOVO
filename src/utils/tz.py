"""Shared timezone helper — reads from settings.yaml."""
from datetime import date, datetime, timezone, timedelta

_tz_cache = None

_OFFSETS = {
    "UTC": 0,
    "Asia/Dubai": 4, "Asia/Muscat": 4,
    "Asia/Riyadh": 3, "Asia/Kuwait": 3, "Asia/Qatar": 3,
    "Asia/Kolkata": 5.5, "Asia/Tokyo": 9, "Asia/Seoul": 9,
    "Asia/Shanghai": 8, "Asia/Hong_Kong": 8, "Asia/Singapore": 8,
    "Europe/London": 0, "Europe/Berlin": 1, "Europe/Paris": 1,
    "Europe/Moscow": 3, "Europe/Istanbul": 3,
    "US/Eastern": -5, "America/New_York": -5,
    "US/Central": -6, "America/Chicago": -6,
    "US/Mountain": -7, "America/Denver": -7,
    "US/Pacific": -8, "America/Los_Angeles": -8,
    "Australia/Sydney": 11, "Pacific/Auckland": 13,
}

def get_tz() -> timezone:
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

def _parse_tz(name: str) -> timezone:
    if name in _OFFSETS:
        return timezone(timedelta(hours=_OFFSETS[name]))
    if name.startswith("UTC"):
        try:
            offset = name[3:].replace(" ", "")
            if offset:
                return timezone(timedelta(hours=float(offset)))
            return timezone.utc
        except (ValueError, IndexError):
            pass
    return timezone.utc

def now() -> datetime:
    return datetime.now(get_tz())

def today() -> date:
    return now().date()
