"""
Extract readable text content from a URL.

Usage as CLI:
    python3 -m src.tools.link_reader "https://example.com"

Usage as module:
    from src.tools.link_reader import extract_sync
    content = extract_sync("https://example.com")
"""
import json
import logging
import re
import sys

import httpx

log = logging.getLogger(__name__)


def extract_sync(url: str, max_chars: int = 4000) -> dict:
    """Fetch a URL and extract readable text. Returns {title, url, content}."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return {"title": "", "url": url, "content": "(beautifulsoup4 not installed)"}

    try:
        resp = httpx.get(
            url,
            follow_redirects=True,
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0 (compatible; KovoBot/1.0)"},
        )
        resp.raise_for_status()
    except Exception as e:
        log.warning("link_reader: fetch failed for %s: %s", url, e)
        return {"title": "", "url": url, "content": f"(could not fetch: {e})"}

    soup = BeautifulSoup(resp.text, "html.parser")

    # Remove non-content elements
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
        tag.decompose()

    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    text = soup.get_text(separator="\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return {"title": title, "url": url, "content": text[:max_chars]}


async def extract_async(url: str, max_chars: int = 4000) -> dict:
    """Async version of extract_sync."""
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, extract_sync, url, max_chars)


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else ""
    if not url:
        print("Usage: python3 -m src.tools.link_reader 'https://...'")
        sys.exit(1)
    result = extract_sync(url)
    print(json.dumps(result, indent=2, ensure_ascii=False))
