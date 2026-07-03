"""
Channels — pluggable chat surfaces (Phase 3e).

    from src.channels import registry
    ch = registry.owner_channel()
    await ch.send_text(chat_id, "…")

Implementations: telegram (full capabilities), dashboard (web chat).
Adding a surface (e.g. MS Teams in v2.1) = one new module implementing
Channel + registration in the gateway; agent core and consumers are
untouched.
"""
from src.channels.base import (  # noqa: F401
    BUTTONS,
    CALLS,
    PHOTOS,
    STREAMING,
    VOICE,
    Channel,
    ChannelCapabilityError,
    ChannelRegistry,
    registry,
)
