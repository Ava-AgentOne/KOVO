"""
Playwright browser automation tool.
Provides an async context-managed browser session.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

log = logging.getLogger(__name__)

_SCREENSHOT_DIR = Path("/opt/kovo/data/screenshots")
_SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


class BrowserSession:
    """Context manager for a single browser session."""

    def __init__(self, headless: bool = True, timeout: int = 30_000):
        self.headless = headless
        self.timeout = timeout
        self._playwright = None
        self._browser = None
        self._page = None

    async def __aenter__(self):
        from playwright.async_api import async_playwright
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=self.headless)
        context = await self._browser.new_context(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )
        self._page = await context.new_page()
        self._page.set_default_timeout(self.timeout)
        return self

    async def __aexit__(self, *_):
        try:
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
        except Exception as e:
            log.warning("Browser cleanup error: %s", e)

    # ---- Navigation ----

    async def goto(self, url: str) -> str:
        """Navigate to URL. Returns final URL."""
        response = await self._page.goto(url, wait_until="domcontentloaded")
        return self._page.url

    async def get_title(self) -> str:
        return await self._page.title()

    async def get_text(self, selector: str = "body") -> str:
        """Extract visible text from the page."""
        try:
            element = await self._page.query_selector(selector)
            if element:
                text = await element.inner_text()
                # Collapse excessive whitespace
                text = re.sub(r"\n{3,}", "\n\n", text)
                text = re.sub(r" {2,}", " ", text)
                return text.strip()
        except Exception as e:
            log.warning("get_text failed: %s", e)
        return ""

    async def get_html(self) -> str:
        return await self._page.content()

    async def screenshot(self, filename: str | None = None) -> str:
        """Take a screenshot. Returns the file path."""
        if filename is None:
            import time
            filename = f"screenshot_{int(time.time())}.png"
        path = str(_SCREENSHOT_DIR / filename)
        await self._page.screenshot(path=path, full_page=True)
        log.info("Screenshot saved: %s", path)
        return path

    async def click(self, selector: str) -> None:
        await self._page.click(selector)

    async def fill(self, selector: str, value: str) -> None:
        await self._page.fill(selector, value)

    async def wait(self, ms: int = 1000) -> None:
        await self._page.wait_for_timeout(ms)

    async def evaluate(self, js: str):
        """Run JavaScript in the page context."""
        return await self._page.evaluate(js)


async def web_search(query: str, max_results: int = 5) -> list[dict]:
    """
    Search DuckDuckGo and return top results.
    Returns list of {title, url, snippet}.
    """
    search_url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"
    results = []

    async with BrowserSession() as browser:
        await browser.goto(search_url)
        await browser.wait(1500)

        try:
            page = browser._page
            result_elements = await page.query_selector_all(".result__body")
            for elem in result_elements[:max_results]:
                try:
                    title_el = await elem.query_selector(".result__title")
                    url_el = await elem.query_selector(".result__url")
                    snippet_el = await elem.query_selector(".result__snippet")

                    title = (await title_el.inner_text()).strip() if title_el else ""
                    url = (await url_el.inner_text()).strip() if url_el else ""
                    snippet = (await snippet_el.inner_text()).strip() if snippet_el else ""

                    if title:
                        results.append({"title": title, "url": url, "snippet": snippet})
                except Exception:
                    continue
        except Exception as e:
            log.warning("Search result extraction failed: %s", e)

    return results


async def fetch_page_text(url: str, max_chars: int = 5000) -> str:
    """Navigate to URL and return page text."""
    async with BrowserSession() as browser:
        await browser.goto(url)
        await browser.wait(1000)
        text = await browser.get_text()
        return text[:max_chars]
