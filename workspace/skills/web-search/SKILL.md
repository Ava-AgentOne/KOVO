---
name: web-search
description: Search the web for current information, news, weather, prices, and facts.
tools: [shell, web_search]
trigger: search, google, look up, find out, what is, news, weather, price, latest, current, today, who is, where is
---

# Web Search Skill

## When to Use
- Questions about current events, news, weather, or prices
- "What is...", "Who is...", "When did..." questions about things you don't know
- Anything that might have changed since your training data

## How to Search
Run the web search tool from the command line:

```bash
python3 -m src.tools.web_search "your search query"
```

This returns JSON with title, url, and snippet for each result.

## How to Read a URL
If a search result looks promising and you need more detail:

```bash
python3 -m src.tools.link_reader "https://example.com/article"
```

This returns the full text content of the page.

## Response Style
- Cite your sources naturally: "According to [source]..."
- Give the answer first, then supporting details
- If results are unclear, say so honestly
