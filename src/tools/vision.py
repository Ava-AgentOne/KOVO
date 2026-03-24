"""
Image analysis via claude -p.

Approach: pass the saved image path directly in the prompt.
Claude Code reads the file itself (vision-capable model) using its
built-in file access — no API key, no base64, no OAuth needed.
Works because call_claude() already uses --permission-mode acceptEdits.

Optional: if the image is > 5 MB, Pillow shrinks it first so Claude
doesn't time out on huge files.
"""
from __future__ import annotations

import asyncio
import logging
from functools import partial
from pathlib import Path

from src.gateway import config as cfg
from src.tools.claude_cli import ClaudeCLIError, call_claude, extract_text

log = logging.getLogger(__name__)

_MAX_BYTES = 5 * 1024 * 1024  # 5 MB — shrink anything larger before passing


def _shrink_if_needed(image_path: str) -> str:
    """
    If the image is > 5 MB, resize it with Pillow and save a smaller copy.
    Returns the path to use (original if small enough, shrunken copy otherwise).
    Silently skips if Pillow is not installed.
    """
    path = Path(image_path)
    if path.stat().st_size <= _MAX_BYTES:
        return image_path

    try:
        import io
        from PIL import Image

        log.info("Image %.1f MB > 5 MB — shrinking before vision call", path.stat().st_size / 1024 / 1024)
        img = Image.open(image_path).convert("RGB")

        for quality in (80, 60, 40):
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=quality, optimize=True)
            if buf.tell() <= _MAX_BYTES:
                small_path = path.with_suffix(".small.jpg")
                small_path.write_bytes(buf.getvalue())
                return str(small_path)

        # Still too big — also scale dimensions
        w, h = img.size
        while w > 200:
            w, h = int(w * 0.7), int(h * 0.7)
            small = img.resize((w, h), Image.LANCZOS)
            buf = io.BytesIO()
            small.save(buf, format="JPEG", quality=40, optimize=True)
            if buf.tell() <= _MAX_BYTES:
                small_path = path.with_suffix(".small.jpg")
                small_path.write_bytes(buf.getvalue())
                return str(small_path)

    except Exception as e:
        log.warning("Image shrink failed (%s) — using original", e)

    return image_path


async def analyze_image(
    image_path: str,
    prompt: str,
    system_prompt: str | None = None,
    model: str = "opus",
) -> str:
    """
    Ask Claude to read and analyze an image file.

    Claude Code reads the file directly from disk using its vision capability.
    The caller must ensure the file exists and is readable.

    Args:
        image_path: Absolute path to the image (JPEG, PNG, etc.)
        prompt: The user's question / instruction about the image.
        system_prompt: Full system prompt (SOUL, memory, skills, etc.)
        model: 'opus' or 'sonnet'. Opus is used by default for vision.

    Returns:
        Claude's text response.

    Raises:
        FileNotFoundError: if image_path does not exist.
        ClaudeCLIError: if claude -p fails.
    """
    if not Path(image_path).exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    use_path = _shrink_if_needed(image_path)

    full_prompt = (
        f"Read and analyze the image at {use_path}.\n\n"
        f"{prompt}"
    )

    loop = asyncio.get_event_loop()
    fn = partial(
        call_claude,
        full_prompt,
        model=model,
        system_prompt=system_prompt,
        timeout=cfg.claude_timeout(),
        # No session_id for vision — keep it stateless so the image
        # context doesn't bleed into the next regular conversation turn.
    )
    response = await loop.run_in_executor(None, fn)
    return extract_text(response)
