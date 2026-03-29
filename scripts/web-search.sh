#!/bin/bash
# Web search wrapper — uses venv python with duckduckgo-search
cd /opt/kovo
/opt/kovo/venv/bin/python3 -m src.tools.web_search "$@"
