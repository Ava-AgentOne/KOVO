#!/bin/bash
# Web search wrapper — uses venv python with duckduckgo-search
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
KOVO_DIR="${KOVO_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)}"
cd "$KOVO_DIR"
"$KOVO_DIR/venv/bin/python3" -m src.tools.web_search "$@"
