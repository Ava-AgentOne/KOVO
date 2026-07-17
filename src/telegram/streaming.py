"""
StreamingReply — live-updating Telegram reply (Phase 3b).

Wraps the send/edit mechanics for streamed agent output:
  * first delta creates a placeholder message,
  * subsequent deltas edit it (throttled — Telegram allows roughly one
    edit per second per chat; we stay at EDIT_INTERVAL),
  * streaming previews are sent as plain text (partial Markdown would
    break parsing on unclosed fences),
  * finalize() renders the definitive text with Markdown + chunking,
    matching the historical non-streaming behavior.

If no delta ever arrives (CLI brain, sub-agent replies, errors) the
placeholder is never created and finalize() simply sends the reply the
old way — callers don't need to know which path ran.
"""
from __future__ import annotations

import logging
import time

log = logging.getLogger(__name__)

EDIT_INTERVAL = 2.0          # seconds between message edits
_PREVIEW_LIMIT = 3900        # keep preview + cursor under Telegram's 4096
_CURSOR = " ▌"


class StreamingReply:
    def __init__(self, msg, interval: float = EDIT_INTERVAL):
        self._msg = msg                 # incoming telegram Message (reply target)
        self._interval = interval
        self._placeholder = None        # our sent message being edited
        self._latest = ""
        self._last_edit = None   # monotonic time of last edit; None = never
        self._last_preview = ""

    # ── streaming callback (wired into agent.handle on_delta) ────────────

    async def on_delta(self, text: str) -> None:
        self._latest = text
        now = time.monotonic()
        # None-check matters: time.monotonic() is small on a freshly booted
        # machine, so `now - 0.0 < interval` would throttle the FIRST delta.
        if self._last_edit is not None and now - self._last_edit < self._interval:
            return
        preview = text[-_PREVIEW_LIMIT:] + _CURSOR
        if preview == self._last_preview:
            return
        try:
            if self._placeholder is None:
                self._placeholder = await self._msg.reply_text(preview)
            else:
                await self._placeholder.edit_text(preview)
            self._last_edit = now
            self._last_preview = preview
        except Exception as e:
            # Streaming is best-effort — never let a preview edit kill the turn
            log.debug("stream edit failed: %s", e)

    # ── completion ────────────────────────────────────────────────────────

    async def discard(self) -> None:
        """Remove the placeholder (permission flow interrupts the reply)."""
        if self._placeholder is not None:
            try:
                await self._placeholder.delete()
            except Exception:
                pass
            self._placeholder = None

    async def finalize(self, text: str, reply_markup=None, reply_fn=None) -> None:
        """Replace the preview with the definitive reply.

        reply_fn: async (chunk, reply_markup) -> None used to send chunks
        (the bot passes _reply_with_retry so retry/Markdown-fallback
        behavior is identical to the non-streaming path).
        """
        chunks = [text[i: i + 4096] for i in range(0, max(len(text), 1), 4096)]

        start = 0
        if self._placeholder is not None:
            # First chunk replaces the placeholder in place
            try:
                from telegram.error import BadRequest
                try:
                    await self._placeholder.edit_text(chunks[0], parse_mode="Markdown")
                except BadRequest:
                    try:
                        await self._placeholder.edit_text(chunks[0])
                    except BadRequest:
                        pass  # e.g. "message is not modified" — preview == final
                start = 1
            except Exception as e:
                log.warning("finalize edit failed (%s) — sending fresh message", e)

        for idx in range(start, len(chunks)):
            if not chunks[idx]:
                continue
            is_last = idx == len(chunks) - 1
            markup = reply_markup if is_last else None
            if reply_fn is not None:
                await reply_fn(self._msg, chunks[idx], reply_markup=markup)
            else:
                await self._msg.reply_text(chunks[idx], reply_markup=markup)

        # Inline keyboards can't ride on an edit we already made; if the whole
        # reply fit in the placeholder but a markup was requested, deliver it
        # on a minimal follow-up so sub-agent recommendation buttons survive.
        if start == 1 and len(chunks) == 1 and reply_markup is not None:
            from telegram import InlineKeyboardMarkup
            if isinstance(reply_markup, InlineKeyboardMarkup):
                try:
                    await self._msg.reply_text("⤴️", reply_markup=reply_markup)
                except Exception:
                    pass

    @property
    def streamed(self) -> bool:
        return self._placeholder is not None
