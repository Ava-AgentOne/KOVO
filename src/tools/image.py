"""
Image tool — search the web for an image and download it locally.

Uses DuckDuckGo image search (duckduckgo-search library).
Falls back to picsum.photos if DDG search fails or returns nothing.
"""
from __future__ import annotations

import logging
import mimetypes
import re
from pathlib import Path

import httpx

log = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}
_SAVE_DIR = Path("/opt/kovo/data/images")
_TIMEOUT = 15


def _save_dir() -> Path:
    _SAVE_DIR.mkdir(parents=True, exist_ok=True)
    return _SAVE_DIR


async def _download(url: str, dest: Path) -> Path:
    """Download a URL to dest, return dest path."""
    async with httpx.AsyncClient(headers=_HEADERS, timeout=_TIMEOUT, follow_redirects=True) as client:
        r = await client.get(url)
        r.raise_for_status()
        dest.write_bytes(r.content)
    return dest


async def _search_ddg(query: str) -> str | None:
    """Return the first image URL from DuckDuckGo image search."""
    try:
        from duckduckgo_search import DDGS  # type: ignore

        results = list(DDGS().images(query, max_results=5))
        for r in results:
            url = r.get("image", "")
            if url and url.startswith("http"):
                return url
    except Exception as e:
        log.warning("DDG image search failed: %s", e)
    return None


async def _fallback_picsum(query: str) -> str:
    """Return a picsum.photos URL (random, seeded by query hash)."""
    seed = abs(hash(query)) % 1000
    return f"https://picsum.photos/seed/{seed}/800/600"


async def fetch_image(query: str, filename: str = "image") -> str | None:
    """
    Search for an image matching `query`, download it, return local file path.
    Returns None if download fails.
    """
    save_dir = _save_dir()

    # 1. Try DuckDuckGo
    url = await _search_ddg(query)
    source = "ddg"

    # 2. Fall back to picsum
    if not url:
        url = await _fallback_picsum(query)
        source = "picsum"

    log.info("image fetch: query=%r url=%s source=%s", query, url[:60], source)

    # Determine extension from URL or content-type
    ext = Path(re.sub(r"\?.*$", "", url)).suffix.lower()
    if ext not in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
        ext = ".jpg"

    dest = save_dir / f"{filename}{ext}"

    try:
        await _download(url, dest)
        log.info("image saved: %s (%d bytes)", dest, dest.stat().st_size)
        return str(dest)
    except Exception as e:
        log.error("image download failed: url=%s error=%s", url, e)
        return None
