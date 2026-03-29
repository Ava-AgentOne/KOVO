#!/bin/bash
# Link reader wrapper — uses venv python with beautifulsoup4
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
KOVO_DIR="${KOVO_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)}"
cd "$KOVO_DIR"
"$KOVO_DIR/venv/bin/python3" -m src.tools.link_reader "$@"
