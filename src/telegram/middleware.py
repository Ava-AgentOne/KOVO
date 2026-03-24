"""
Telegram middleware: authentication (allowlist) and basic rate limiting.
"""
import logging
import time
from collections import defaultdict

from telegram import Update
from telegram.ext import ContextTypes

log = logging.getLogger(__name__)

# Per-user rate limit: max N messages per window
_RATE_LIMIT = 20       # messages
_RATE_WINDOW = 60      # seconds
_rate_counters: dict[int, list[float]] = defaultdict(list)


def is_allowed(user_id: int, allowed_users: list[int]) -> bool:
    return user_id in allowed_users


def check_rate_limit(user_id: int) -> bool:
    """Returns True if the user is within the rate limit."""
    now = time.monotonic()
    timestamps = _rate_counters[user_id]
    # Drop timestamps outside the window
    _rate_counters[user_id] = [t for t in timestamps if now - t < _RATE_WINDOW]
    if len(_rate_counters[user_id]) >= _RATE_LIMIT:
        return False
    _rate_counters[user_id].append(now)
    return True


async def auth_middleware(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    allowed_users: list[int],
) -> bool:
    """
    Returns True if the update should be processed.
    Sends an error message and returns False otherwise.
    """
    user = update.effective_user
    if user is None:
        return False

    if not is_allowed(user.id, allowed_users):
        log.warning("Unauthorized access attempt from user_id=%s", user.id)
        if update.message:
            await update.message.reply_text("Unauthorized.")
        return False

    if not check_rate_limit(user.id):
        log.warning("Rate limit exceeded for user_id=%s", user.id)
        if update.message:
            await update.message.reply_text("Slow down — too many messages.")
        return False

    return True
