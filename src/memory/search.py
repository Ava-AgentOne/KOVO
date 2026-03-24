"""
Simple keyword search across all Markdown files in the workspace.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

log = logging.getLogger(__name__)


def search(
    workspace: Path,
    query: str,
    max_results: int = 10,
    include_dirs: list[str] | None = None,
) -> list[dict]:
    """
    Keyword search across .md files under workspace.
    Returns list of {file, score, preview} sorted by relevance.

    include_dirs: restrict to specific subdirs (e.g. ["memory", "skills"]).
                  None = search everywhere.
    """
    query_words = [w.lower() for w in query.split() if len(w) > 2]
    if not query_words:
        return []

    pattern = re.compile("|".join(re.escape(w) for w in query_words), re.IGNORECASE)
    results: list[dict] = []

    search_root = workspace
    if include_dirs:
        search_paths = [workspace / d for d in include_dirs if (workspace / d).exists()]
    else:
        search_paths = [workspace]

    seen: set[Path] = set()
    for base in search_paths:
        for md_file in base.rglob("*.md"):
            if md_file in seen:
                continue
            seen.add(md_file)
            try:
                content = md_file.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            matches = pattern.findall(content)
            if not matches:
                continue

            score = len(matches)
            lines = content.splitlines()
            preview_lines = [l.strip() for l in lines if pattern.search(l)][:4]
            preview = "\n".join(preview_lines)

            try:
                rel = md_file.relative_to(workspace)
            except ValueError:
                rel = md_file

            results.append({"file": str(rel), "score": score, "preview": preview})

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:max_results]
