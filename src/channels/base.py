"""
Channel interface — pluggable chat surfaces (v2.0 architecture, Phase 3e).

A Channel is a way to reach the owner: Telegram today, the dashboard chat,
MS Teams or others later. The agent core stays channel-agnostic — it
produces markdown text and tool calls; channels own delivery (chunking,
formatting quirks, lifecycle). Consumers (heartbeat alerts, reminders,
native tools) send through the registry instead of holding a bot object,
so adding a new surface never touches them.

Capabilities let callers degrade gracefully: a channel that can't send
photos gets a text fallback, one that can't stream gets the final reply
only.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod

log = logging.getLogger(__name__)

# Known capability flags
STREAMING = "streaming"   # live-updating replies
PHOTOS = "photos"         # send_photo
VOICE = "voice"           # send_voice
BUTTONS = "buttons"       # inline keyboards / rich replies
CALLS = "calls"           # real voice calls (Telegram-only today)


class ChannelCapabilityError(RuntimeError):
    """Raised when a channel is asked for something it can't do."""


class Channel(ABC):
    """Common interface for chat surfaces."""

    name: str = "base"
    capabilities: frozenset = frozenset()

    def can(self, capability: str) -> bool:
        return capability in self.capabilities

    # ── lifecycle (no-ops for surfaces without their own connection) ──────

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    # ── outbound ──────────────────────────────────────────────────────────

    @abstractmethod
    async def send_text(self, chat_id, text: str, markdown: bool = True) -> None:
        """Deliver text to a chat, handling the channel's length limits."""

    async def send_photo(self, chat_id, path: str, caption: str = "") -> None:
        raise ChannelCapabilityError(f"{self.name} cannot send photos")

    async def send_voice(self, chat_id, path: str, caption: str = "") -> None:
        raise ChannelCapabilityError(f"{self.name} cannot send voice notes")


class ChannelRegistry:
    """name → Channel. The gateway populates it at startup from config."""

    def __init__(self):
        self._channels: dict[str, Channel] = {}

    def register(self, channel: Channel) -> None:
        self._channels[channel.name] = channel
        log.info("Channel registered: %s (capabilities: %s)",
                 channel.name, ", ".join(sorted(channel.capabilities)) or "none")

    def get(self, name: str) -> Channel | None:
        return self._channels.get(name)

    def all(self) -> list[Channel]:
        return list(self._channels.values())

    def owner_channel(self) -> Channel | None:
        """The owner's preferred channel (settings.yaml channels.default)."""
        try:
            from src.gateway import config as cfg
            preferred = str(cfg.get().get("channels", {}).get("default", "telegram"))
        except Exception:
            preferred = "telegram"
        return (
            self._channels.get(preferred)
            or self._channels.get("telegram")
            or next(iter(self._channels.values()), None)
        )


# Module singleton — populated by the gateway, read by consumers.
registry = ChannelRegistry()
