"""
Web search using DuckDuckGo — no API key needed.

Usage as CLI (for Claude Code tool use):
    python3 -m src.tools.web_search "your query"

Usage as module:
    from src.tools.web_search import search
    results = search("weather Dubai")
"""
import json
import logging
import sys

log = logging.getLogger(__name__)


def search(query: str, max_results: int = 5) -> list[dict]:
    """Search the web and return results as a list of dicts."""
    try:
        from ddgs import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                })
        return results
    except Exception as e:
        log.error("Web search failed: %s", e)
        return [{"error": str(e)}]


def format_results(results: list[dict]) -> str:
    """Format search results as readable text for the agent."""
    if not results:
        return "No results found."
    if results[0].get("error"):
        return f"Search error: {results[0]['error']}"
    lines = []
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. **{r['title']}**")
        lines.append(f"   {r['snippet']}")
        lines.append(f"   {r['url']}")
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
    if not query:
        print("Usage: python3 -m src.tools.web_search 'your query'")
        sys.exit(1)
    results = search(query)
    print(json.dumps(results, indent=2))
