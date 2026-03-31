#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
KOVO_DIR="${KOVO_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)}"
G='\033[38;5;114m' R='\033[38;5;203m' B='\033[38;5;75m' N='\033[0m' DM='\033[2m'
echo -e "\n${B}KOVO Health Check${N} ${DM}$(date '+%Y-%m-%d %H:%M')${N}\n"
c() { if eval "$2" &>/dev/null; then echo -e "  ${G}✓${N} $1"; else echo -e "  ${R}✗${N} $1"; fi; }
if [[ "$(uname)" == "Darwin" ]]; then
    c "KOVO service" "launchctl list com.kovo.agent 2>/dev/null | grep -q PID"
else
    c "KOVO service" "systemctl is-active --quiet kovo"
fi
c "Redis" "redis-cli ping | grep -q PONG"
c "Python venv" "[ -f $KOVO_DIR/venv/bin/python ]"
c "Claude CLI" "command -v claude"
echo ""
