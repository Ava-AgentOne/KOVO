---
name: browser
description: Automate web browsing — navigate pages, extract content, take screenshots, fill forms
tools: [playwright]
trigger: browse, website, web, url, scrape, screenshot, open page, click, fill form, extract, search online, look up online, visit
---

# Browser Skill

## Capabilities
- Navigate to any URL
- Extract visible text content from a page
- Take full-page screenshots
- Click elements and fill forms
- Search the web via DuckDuckGo

## Procedures

### Navigate and Extract Text
1. `go_to(url)` — navigate to page
2. `get_text()` — extract visible text (cleaned)
3. `screenshot(path)` — take a screenshot

### Search the Web
`web_search(query)` — uses DuckDuckGo, returns top results.

### Fill a Form
1. `go_to(url)`
2. `fill(selector, value)` for each field
3. `click(selector)` to submit

## Notes
- Runs headless Chromium
- Times out after 30s per action
- JavaScript-heavy pages may need a short wait
- Screenshots saved to /opt/miniclaw/data/screenshots/
