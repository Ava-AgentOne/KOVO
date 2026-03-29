#!/bin/bash
# Link reader wrapper — uses venv python with beautifulsoup4
cd /opt/kovo
/opt/kovo/venv/bin/python3 -m src.tools.link_reader "$@"
