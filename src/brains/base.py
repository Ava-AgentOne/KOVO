"""
Brain interface — pluggable AI backends (v2.0 architecture).

A Brain turns a prompt into a reply dict. KOVO ships two Claude brains —
the historical `claude -p` subprocess and the Claude Agent SDK — selected
via settings.yaml:

    brains:
      claude: sdk    # or: cli (default)

The generate() contract mirrors the historical call_claude() so every
existing caller works unchanged regardless of the active brain. Streaming
is added in Phase 3b; additional providers (Ollama chat, others) become
new Brain subclasses without touching the agent core.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class Brain(ABC):
    """Common interface for AI backends."""

    name: str = "base"
    supports_streaming: bool = False

    @abstractmethod
    def generate(
        self,
        prompt: str,
        session_id: str | None = None,
        model: str | None = None,
        system_prompt: str | None = None,
        timeout: int = 600,
        files: list[str] | None = None,
    ) -> dict:
        """Return a dict shaped like the claude -p JSON response.

        Keys on success: result (text), session_id, total_cost_usd, usage.
        May instead return the {"__permission_needed__": True, ...} sentinel
        when a command was blocked by the sandbox allowlist.
        """

    async def generate_stream(
        self,
        prompt: str,
        session_id: str | None = None,
        model: str | None = None,
        system_prompt: str | None = None,
        timeout: int = 600,
        files: list[str] | None = None,
        on_delta=None,
    ) -> dict:
        """Async variant that reports progress (Phase 3b).

        on_delta: async callable awaited with the accumulated reply text as
        it grows. The final return dict is identical to generate()'s. Brains
        that don't stream (supports_streaming=False) don't implement this.
        """
        raise NotImplementedError(f"{self.name} does not support streaming")
