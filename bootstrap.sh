#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
KOVO_VERSION="0.8"
# KOVO — Self-Hosted AI Agent Installer v5.1
# https://github.com/Ava-AgentOne/kovo
#
# Usage:
#   bash bootstrap.sh              # Interactive mode (recommended)
#   bash bootstrap.sh --resume     # Resume a failed/interrupted install
#   bash bootstrap.sh --yes        # Auto-accept all prompts
#   bash bootstrap.sh --uninstall  # Clean removal
#
# Requirements: Ubuntu 24.04+ or macOS 13+ · 8GB+ RAM · 30GB+ free disk
# License: GNU AGPLv3
# ═══════════════════════════════════════════════════════════════════

set -euo pipefail

INSTALLER_VERSION="5.2"

# ─── Cross-platform detection ────────────────────────────────────
OS_TYPE="$(uname -s)"
case "$OS_TYPE" in
    Linux)  KOVO_DIR="/opt/kovo" ;;
    Darwin) KOVO_DIR="$HOME/.kovo" ;;
    *)      echo "Unsupported OS: $OS_TYPE"; exit 1 ;;
esac

# On macOS, ensure Homebrew is in PATH for all phases
if [[ "$OS_TYPE" == "Darwin" ]]; then
    eval "$(/opt/homebrew/bin/brew shellenv 2>/dev/null || /usr/local/bin/brew shellenv 2>/dev/null || true)"
fi

VENV="$KOVO_DIR/venv"
WORKSPACE="$KOVO_DIR/workspace"
STATE_FILE="/tmp/.kovo-install-state"
LOG_FILE="/tmp/kovo-install.log"
KOVO_REPO="https://github.com/Ava-AgentOne/kovo.git"
MASCOT_URL="https://raw.githubusercontent.com/Ava-AgentOne/kovo/main/assets/kovo-mascot.png"

RESUME=false
AUTO_YES=false
UNINSTALL=false
for arg in "$@"; do
    case "$arg" in
        --resume)    RESUME=true ;;
        --yes|-y)    AUTO_YES=true ;;
        --uninstall) UNINSTALL=true ;;
        --help|-h)   echo "Usage: bash bootstrap.sh [--resume] [--yes] [--uninstall]"; exit 0 ;;
    esac
done

# ─── Terminal Colors ──────────────────────────────────────────────
if [[ -t 1 ]]; then
    BOLD='\033[1m' DIM='\033[2m'
    BLUE='\033[38;5;75m' CYAN='\033[38;5;80m' GREEN='\033[38;5;114m'
    YELLOW='\033[38;5;221m' RED='\033[38;5;203m' PINK='\033[38;5;211m'
    GRAY='\033[38;5;245m' WHITE='\033[38;5;255m' NC='\033[0m'
else
    BOLD='' DIM='' BLUE='' CYAN='' GREEN='' YELLOW='' RED='' PINK='' GRAY='' WHITE='' NC=''
fi

# Save stdin before tee redirect (process substitution breaks stdin)
exec 3<&0
exec > >(tee -a "$LOG_FILE") 2>&1

ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
warn() { echo -e "  ${YELLOW}⚠${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1"; }
info() { echo -e "  ${BLUE}→${NC} $1"; }
dim()  { echo -e "  ${GRAY}$1${NC}"; }

# Background spinner for long-running commands (bash 3.2 safe)
spin() {
    local pid=$1 label="${2:-Working...}"
    local i=0
    while kill -0 "$pid" 2>/dev/null; do
        case $((i % 4)) in
            0) printf "\r  ${BLUE}-${NC} %s " "$label" > /dev/tty ;;
            1) printf "\r  ${BLUE}\\${NC} %s " "$label" > /dev/tty ;;
            2) printf "\r  ${BLUE}|${NC} %s " "$label" > /dev/tty ;;
            3) printf "\r  ${BLUE}/${NC} %s " "$label" > /dev/tty ;;
        esac
        i=$((i + 1))
        sleep 0.2
    done
    printf "\r%*s\r" 70 "" > /dev/tty
}

# Run a command with a spinner — usage: run_with_spin "label" command arg1 arg2
run_with_spin() {
    local label="$1"; shift
    "$@" > /tmp/.kovo-cmd-out 2>&1 &
    local pid=$!
    spin $pid "$label"
    local rc=0
    wait $pid || rc=$?
    return $rc
}

progress_bar() {
    local current="$1" total="$2"
    local pct=$((current * 100 / total))
    local filled=$((pct / 2)) empty=$((50 - pct / 2))
    local bar="${BLUE}"
    for ((i=0; i<filled; i++)); do bar+="█"; done
    bar+="${GRAY}"
    for ((i=0; i<empty; i++)); do bar+="░"; done
    echo -e "  ${bar}${NC} ${WHITE}${pct}%${NC}"
}

confirm() {
    local prompt="$1"
    if $AUTO_YES; then return 0; fi
    echo -en "  ${PINK}?${NC} ${prompt} ${DIM}[Y/n]${NC}: "
    read -r answer <&3
    [[ "$answer" != "n" && "$answer" != "N" ]]
}

save_state() { echo "$1" > "$STATE_FILE"; }
load_state() { [[ -f "$STATE_FILE" ]] && cat "$STATE_FILE" || echo "0"; }
clear_state() { rm -f "$STATE_FILE"; }

trap_handler() {
    local exit_code=$?
    if [[ $exit_code -ne 0 ]]; then
        echo ""
        fail "Installation interrupted at phase $(load_state)."
        echo -e "  ${YELLOW}Resume:${NC} ${WHITE}bash bootstrap.sh --resume${NC}"
        echo -e "  ${GRAY}Log: ${LOG_FILE}${NC}"
        echo ""
    fi
}
trap trap_handler EXIT

# ─── Screen Management ───────────────────────────────────────────
# Clears terminal, shows logo, shows step indicator dots
new_screen() {
    local step=${1:-0} total=8
    clear
    local LB='\033[38;5;117m'
    local KB='\033[38;5;75m'
    local WH='\033[38;5;255m'
    local DK='\033[38;5;24m'
    local CH='\033[38;5;216m'
    local SM='\033[38;5;153m'
    local OR='\033[38;5;208m'
    local GY='\033[38;5;242m'
    echo ""
    echo -e "${LB}       ##*${NC}"
    echo -e "${LB}       ###       ###${NC}"
    echo -e "${KB}        ++       ++${NC}"
    echo -e "${KB}         ++     ++${NC}"
    echo -e "${KB}     +++++++++++++++++${NC}"
    echo -e "${KB}   +++++++++++++++++++++${NC}       ${KB}${BOLD}██╗  ██╗  ██████╗  ██╗   ██╗  ██████╗${NC}"
    echo -e "${KB}   +++++${WH}*##*${KB}+++${WH}*##*${KB}+++++${NC}       ${KB}${BOLD}██║ ██╔╝ ██╔═══██╗ ██║   ██║ ██╔═══██╗${NC}"
    echo -e "${KB}   +++${WH}#@@@@@@${KB}+${WH}@@@@@@%${KB}+++${NC}       ${KB}${BOLD}█████╔╝  ██║   ██║ ██║   ██║ ██║   ██║${NC}"
    echo -e "${KB}   +++${WH}%@${DK}*:-*${WH}+@@@${DK}-:=${WH}*${KB}++++${NC}       ${KB}${BOLD}██╔═██╗  ██║   ██║ ╚██╗ ██╔╝ ██║   ██║${NC}"
    echo -e "${KB}   +++${WH}%@#${DK}:+:${WH}-%@@${DK}==-:${KB}++++${NC}       ${KB}${BOLD}██║  ██╗ ╚██████╔╝  ╚████╔╝  ╚██████╔╝${NC}"
    echo -e "${KB}   +${CH}****${WH}@@@%${KB}+++${WH}%@@@${CH}****${KB}+${NC}       ${KB}${BOLD}╚═╝  ╚═╝  ╚═════╝    ╚═══╝    ╚═════╝${NC}"
    echo -e "${KB}   +++++++${WH}**${KB}+++${WH}*#${KB}+++++++${NC}"
    echo -e "${KB}   +++++++++${SM}###${KB}+++++++++${NC}       ${CYAN}Self-hosted AI agent${NC}"
    echo -e "${KB}   +++++++++++++++++++++${NC}       ${GY}v${KOVO_VERSION} · Powered by Claude Code · GNU AGPLv3${NC}"
    echo -e "${KB}     +++++++++++++++++${NC}         ${OR}Created by: Esam AlRemeithi${NC}"
    echo ""
    if (( step > 0 )); then
        local dots="   "
        for ((i=1; i<=total; i++)); do
            if (( i < step )); then dots+="${GREEN}●${NC} "
            elif (( i == step )); then dots+="${BLUE}●${NC} "
            else dots+="${GRAY}○${NC} "; fi
        done
        echo -e "$dots"
    fi
    echo ""
}

# Navigation for wizard screens (phases 1-4) — supports [B]ack
# Returns 0 = continue forward, 1 = go back
wizard_nav() {
    local step=$1
    echo ""
    echo -e "  ${BLUE}──────────────────────────────────────────────────────────${NC}"
    if (( step > 1 )); then
        echo -en "  ${DIM}[B] Back${NC}  │  ${WHITE}[Enter] Continue${NC}: "
    else
        echo -en "  ${WHITE}[Enter] Continue${NC}: "
    fi
    read -r nav <&3
    [[ "$nav" == "b" || "$nav" == "B" ]] && (( step > 1 )) && return 1
    return 0
}

# ─── Mascot Display ──────────────────────────────────────────────
show_mascot() {
    local img_path="$1"
    "$VENV/bin/python" << MASCOT_PYEOF
from PIL import Image
img = Image.open("$img_path").convert('RGBA')
W, H = 36, int(36 * img.height / img.width)
H += H % 2
img = img.resize((W, H), Image.LANCZOS)
R = "\033[0m"
for y in range(0, H, 2):
    line = ""
    for x in range(W):
        r1,g1,b1,a1 = img.getpixel((x,y))
        r2,g2,b2,a2 = img.getpixel((x,y+1)) if y+1<H else (0,0,0,0)
        t = a1<40 or (r1<15 and g1<15 and b1<15)
        b = a2<40 or (r2<15 and g2<15 and b2<15)
        if t and b: line+=" "
        elif t: line+=f"\033[38;2;{r2};{g2};{b2}m▄{R}"
        elif b: line+=f"\033[38;2;{r1};{g1};{b1}m▀{R}"
        else: line+=f"\033[38;2;{r1};{g1};{b1}m\033[48;2;{r2};{g2};{b2}m▀{R}"
    print(line.rstrip())
MASCOT_PYEOF
}

# ═══════════════════════════════════════════════════════════════════
#  UNINSTALL
# ═══════════════════════════════════════════════════════════════════
if $UNINSTALL; then
    new_screen
    echo -e "  ${RED}${BOLD}Uninstall KOVO${NC}"
    echo ""
    warn "This will remove KOVO and all its data."
    if ! confirm "Are you sure?"; then echo "  Cancelled."; exit 0; fi
    echo ""
    info "Stopping service..."
    if [[ "$OS_TYPE" == "Darwin" ]]; then
        launchctl unload ~/Library/LaunchAgents/com.kovo.agent.plist 2>/dev/null || true
        rm -f ~/Library/LaunchAgents/com.kovo.agent.plist
    else
        sudo systemctl stop kovo 2>/dev/null || true
        sudo systemctl disable kovo 2>/dev/null || true
        sudo rm -f /etc/systemd/system/kovo.service
        sudo systemctl daemon-reload
        sudo rm -f /etc/sudoers.d/kovo /etc/logrotate.d/kovo
    fi
    info "Removing $KOVO_DIR..."
    if [[ "$OS_TYPE" == "Darwin" ]]; then
        rm -rf "$KOVO_DIR"
    else
        sudo rm -rf "$KOVO_DIR"
    fi
    echo ""
    ok "KOVO has been uninstalled."
    exit 0
fi

# ═══════════════════════════════════════════════════════════════════
#  WIZARD SCREEN 1 — Welcome + Pre-flight
# ═══════════════════════════════════════════════════════════════════
screen_welcome() {
    new_screen 1

    echo -e "  ${DIM}KOVO is a personal AI agent that lives on your server.${NC}"
    echo -e "  ${DIM}It uses ${CYAN}Claude Code CLI${DIM} as its brain, communicates via${NC}"
    echo -e "  ${DIM}${CYAN}Telegram${DIM}, and manages itself through a ${CYAN}web dashboard${DIM}.${NC}"
    echo ""
    echo -e "  ${WHITE}This installer will:${NC}"
    echo -e "    ${BLUE}1.${NC} Check your system meets requirements"
    echo -e "    ${BLUE}2.${NC} Authenticate your Claude subscription"
    echo -e "    ${BLUE}3.${NC} Install all packages, tools, and skills"
    echo -e "    ${BLUE}4.${NC} Set up the agent framework"
    echo -e "    ${BLUE}5.${NC} Build and launch the dashboard for final config"
    echo ""
    echo -e "  ${WHITE}You'll need:${NC}"
    echo -e "    ${DIM}•${NC} A ${WHITE}Claude Max${NC} or ${WHITE}Team${NC} subscription"
    echo -e "    ${DIM}•${NC} A web browser to complete setup"
    echo ""
    echo -e "  ${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "  ${BOLD}${WHITE}Pre-flight Checks${NC}"
    echo -e "  ${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    local errors=0

    if [[ "$OS_TYPE" == "Darwin" ]]; then
        local mac_ver=$(sw_vers -productVersion 2>/dev/null || echo "unknown")
        ok "OS: macOS $mac_ver"
    elif [[ -f /etc/os-release ]]; then
        source /etc/os-release
        if [[ "$ID" == "ubuntu" ]]; then
            local ver_major="${VERSION_ID%%.*}"
            if (( ver_major >= 24 )); then ok "OS: $PRETTY_NAME"
            else warn "Ubuntu $VERSION_ID — 24.04+ recommended"; fi
        else warn "Non-Ubuntu OS ($ID)"; fi
    else fail "Cannot detect OS"; errors=$((errors+1)); fi

    if [[ "$OS_TYPE" == "Darwin" ]]; then
        local ram_mb=$(( $(sysctl -n hw.memsize) / 1048576 ))
    else
        local ram_mb=$(free -m | awk '/^Mem:/{print $2}')
    fi
    if (( ram_mb >= 7000 )); then ok "RAM: ${ram_mb}MB ($(( ram_mb / 1024 ))GB)"
    elif (( ram_mb >= 4000 )); then warn "RAM: ${ram_mb}MB — 8GB+ recommended"
    else fail "RAM: ${ram_mb}MB — minimum 4GB"; errors=$((errors+1)); fi

    if [[ "$OS_TYPE" == "Darwin" ]]; then
        local disk_gb=$(df -g / | tail -1 | awk '{print $4}')
    else
        local disk_gb=$(( $(df / --output=avail | tail -1 | tr -d ' ') / 1048576 ))
    fi
    if (( disk_gb >= 30 )); then ok "Disk: ${disk_gb}GB available"
    elif (( disk_gb >= 15 )); then warn "Disk: ${disk_gb}GB — 30GB+ recommended"
    else fail "Disk: ${disk_gb}GB — need 15GB+"; errors=$((errors+1)); fi

    if curl -sf --max-time 5 https://pypi.org > /dev/null 2>&1; then ok "Internet: connected"
    else fail "Internet: no connection"; errors=$((errors+1)); fi

    if [[ "$OS_TYPE" == "Darwin" ]]; then
        ok "Sudo: not required on macOS"
    elif sudo -n true 2>/dev/null; then ok "Sudo: available"
    elif sudo true; then ok "Sudo: available"
    else fail "Sudo: not available"; errors=$((errors+1)); fi

    if command -v python3 &>/dev/null; then ok "Python: $(python3 --version | cut -d' ' -f2)"
    elif [[ "$OS_TYPE" == "Darwin" ]]; then warn "Python3: not found (will be installed by Homebrew)"
    else fail "Python3: not found"; errors=$((errors+1)); fi

    if [[ "$OS_TYPE" == "Darwin" ]]; then
        if ! lsof -i :8080 -sTCP:LISTEN &>/dev/null; then ok "Port 8080: available"
        else warn "Port 8080: in use"; fi
        if ! lsof -i :3000 -sTCP:LISTEN &>/dev/null; then ok "Port 3000: available"
        else warn "Port 3000: in use"; fi
    else
        if ! ss -tlnp | grep -q ':8080 ' 2>/dev/null; then ok "Port 8080: available"
        else warn "Port 8080: in use"; fi
        if ! ss -tlnp | grep -q ':3000 ' 2>/dev/null; then ok "Port 3000: available"
        else warn "Port 3000: in use"; fi
    fi

    if [[ -d "$KOVO_DIR" ]] && ! $RESUME; then
        warn "Existing KOVO install at $KOVO_DIR"
        if ! confirm "Overwrite?"; then echo "  Use --resume to continue."; exit 0; fi
    fi

    echo ""
    if (( errors > 0 )); then
        fail "$errors check(s) failed. Fix the issues above and re-run."
        exit 1
    fi
    ok "All pre-flight checks passed"
}

# ═══════════════════════════════════════════════════════════════════
#  WIZARD SCREEN 2 — Claude Code Authentication
# ═══════════════════════════════════════════════════════════════════
screen_claude_auth() {
    new_screen 2

    echo -e "  ${BOLD}${WHITE}Claude Code Authentication${NC}"
    echo ""
    echo -e "  KOVO uses ${WHITE}Claude Code CLI${NC} as its brain. It runs Claude"
    echo -e "  as a subprocess (${DIM}claude -p${NC}) to handle complex tasks."
    echo ""
    echo -e "  This requires a ${WHITE}Claude Max${NC} or ${WHITE}Team${NC} subscription."
    echo ""

    if command -v claude &>/dev/null; then
        local claude_ver=$(claude --version 2>/dev/null || echo "")
        if [[ -n "$claude_ver" ]]; then ok "Claude Code CLI: $claude_ver"; fi
    fi

    echo -e "  ${BLUE}┌──────────────────────────────────────────────────┐${NC}"
    echo -e "  ${BLUE}│${NC}                                                  ${BLUE}│${NC}"
    echo -e "  ${BLUE}│${NC}  ${WHITE}Step 1:${NC} Open ${YELLOW}another terminal tab${NC} and run:         ${BLUE}│${NC}"
    echo -e "  ${BLUE}│${NC}                                                  ${BLUE}│${NC}"
    echo -e "  ${BLUE}│${NC}    ${CYAN}claude login${NC}                                   ${BLUE}│${NC}"
    echo -e "  ${BLUE}│${NC}                                                  ${BLUE}│${NC}"
    echo -e "  ${BLUE}│${NC}  This opens a browser URL. Log in with your      ${BLUE}│${NC}"
    echo -e "  ${BLUE}│${NC}  Anthropic account, authorize the CLI, and it    ${BLUE}│${NC}"
    echo -e "  ${BLUE}│${NC}  stores your session automatically.              ${BLUE}│${NC}"
    echo -e "  ${BLUE}│${NC}                                                  ${BLUE}│${NC}"
    echo -e "  ${BLUE}│${NC}  ${WHITE}Step 2:${NC} Come back here when it says \"Logged in\"  ${BLUE}│${NC}"
    echo -e "  ${BLUE}│${NC}                                                  ${BLUE}│${NC}"
    echo -e "  ${BLUE}└──────────────────────────────────────────────────┘${NC}"
    echo ""

    if confirm "Have you completed 'claude login'?"; then
        info "Verifying..."
        if command -v claude &>/dev/null; then ok "Claude Code CLI: ready"
        else warn "CLI not installed yet — will install in Phase 5"; fi
    else
        warn "Skipping — authenticate later with: claude login"
    fi
}

# ═══════════════════════════════════════════════════════════════════
#  WIZARD SCREEN 3 — Network Configuration
# ═══════════════════════════════════════════════════════════════════
GATEWAY_PORT="8080"
DASHBOARD_PORT="3000"

screen_network() {
    new_screen 3

    echo -e "  ${BOLD}${WHITE}Network Configuration${NC}"
    echo ""
    echo -e "  KOVO runs two web services on your VM:"
    echo ""
    echo -e "  ${WHITE}Gateway${NC} ${DIM}(default: 8080)${NC}"
    echo -e "    The main API server. Handles Telegram webhooks,"
    echo -e "    the chat WebSocket, and serves the production"
    echo -e "    dashboard. This is the port you'll access KOVO on."
    echo -e "    Example: ${CYAN}http://$({ hostname -I 2>/dev/null || ipconfig getifaddr en0 2>/dev/null; } | awk '{print $1}' || echo 'your-ip'):8080${NC}"
    echo ""
    echo -e "  ${WHITE}Dashboard dev server${NC} ${DIM}(default: 3000)${NC}"
    echo -e "    Only used during development. The gateway serves"
    echo -e "    the built dashboard in production."
    echo ""

    if confirm "Use default ports (8080 + 3000)?"; then
        GATEWAY_PORT="8080"
        DASHBOARD_PORT="3000"
    else
        echo -en "  ${PINK}?${NC} Gateway port ${DIM}[8080]${NC}: "
        read -r gp <&3
        GATEWAY_PORT="${gp:-8080}"
        echo -en "  ${PINK}?${NC} Dashboard dev port ${DIM}[3000]${NC}: "
        read -r dp <&3
        DASHBOARD_PORT="${dp:-3000}"
    fi

    ok "Gateway:   :${GATEWAY_PORT}"
    ok "Dashboard: :${DASHBOARD_PORT}"
}

# ═══════════════════════════════════════════════════════════════════
#  WIZARD SCREEN 4 — Installation Overview
# ═══════════════════════════════════════════════════════════════════
screen_overview() {
    new_screen 4

    echo -e "  ${BOLD}${WHITE}Installation Overview${NC}"
    echo ""
    echo -e "  ${WHITE}Tools${NC} ${DIM}(9 — KOVO's capabilities)${NC}"
    echo -e "  ${BLUE}┌────────────────────┬──────────────────────────────┐${NC}"
    echo -e "  ${BLUE}│${NC} ${CYAN}shell${NC}              ${BLUE}│${NC} Run commands, manage files    ${BLUE}│${NC}"
    echo -e "  ${BLUE}│${NC} ${CYAN}claude_cli${NC}         ${BLUE}│${NC} Claude Code for reasoning     ${BLUE}│${NC}"
    echo -e "  ${BLUE}│${NC} ${CYAN}browser${NC}            ${BLUE}│${NC} Playwright headless Chromium  ${BLUE}│${NC}"
    echo -e "  ${BLUE}│${NC} ${CYAN}tts${NC}                ${BLUE}│${NC} Text-to-speech (edge-tts)     ${BLUE}│${NC}"
    echo -e "  ${BLUE}│${NC} ${CYAN}whisper${NC}            ${BLUE}│${NC} Voice transcription (Groq)    ${BLUE}│${NC}"
    echo -e "  ${BLUE}│${NC} ${CYAN}telegram_call${NC}      ${BLUE}│${NC} Voice calls via Pyrogram      ${BLUE}│${NC}"
    echo -e "  ${BLUE}│${NC} ${CYAN}google_api${NC}         ${BLUE}│${NC} Drive, Docs, Gmail, Calendar  ${BLUE}│${NC}"
    echo -e "  ${BLUE}│${NC} ${CYAN}github${NC}             ${BLUE}│${NC} Repos, issues, PRs            ${BLUE}│${NC}"
    echo -e "  ${BLUE}│${NC} ${CYAN}ollama${NC}             ${BLUE}│${NC} Local LLM for cheap tasks     ${BLUE}│${NC}"
    echo -e "  ${BLUE}└────────────────────┴──────────────────────────────┘${NC}"
    echo ""
    echo -e "  ${WHITE}Skills${NC} ${DIM}(6 default)${NC}"
    echo -e "  ${BLUE}┌────────────────────┬──────────────────────────────┐${NC}"
    echo -e "  ${BLUE}│${NC} ${PINK}report-builder${NC}     ${BLUE}│${NC} HTML reports, dashboards      ${BLUE}│${NC}"
    echo -e "  ${BLUE}│${NC} ${PINK}security-audit${NC}     ${BLUE}│${NC} VM security scan + baseline   ${BLUE}│${NC}"
    echo -e "  ${BLUE}│${NC} ${PINK}server-health${NC}      ${BLUE}│${NC} System health monitoring      ${BLUE}│${NC}"
    echo -e "  ${BLUE}│${NC} ${PINK}google-workspace${NC}   ${BLUE}│${NC} Docs, Drive, Gmail procedures ${BLUE}│${NC}"
    echo -e "  ${BLUE}│${NC} ${PINK}browser${NC}            ${BLUE}│${NC} Web scraping + screenshots    ${BLUE}│${NC}"
    echo -e "  ${BLUE}│${NC} ${PINK}phone-call${NC}         ${BLUE}│${NC} Voice call procedures         ${BLUE}│${NC}"
    echo -e "  ${BLUE}└────────────────────┴──────────────────────────────┘${NC}"
    echo ""
    echo -e "  ${WHITE}Security${NC} ${DIM}(always included)${NC}"
    echo -e "  ${BLUE}┌────────────────────┬──────────────────────────────┐${NC}"
    echo -e "  ${BLUE}│${NC} ${GREEN}ClamAV${NC}             ${BLUE}│${NC} Antivirus scanner            ${BLUE}│${NC}"
    echo -e "  ${BLUE}│${NC} ${GREEN}chkrootkit${NC}         ${BLUE}│${NC} Rootkit detection            ${BLUE}│${NC}"
    echo -e "  ${BLUE}│${NC} ${GREEN}rkhunter${NC}           ${BLUE}│${NC} Rootkit hunter               ${BLUE}│${NC}"
    echo -e "  ${BLUE}└────────────────────┴──────────────────────────────┘${NC}"
    echo ""
    echo -e "  ${WHITE}Packages:${NC} ${DIM}Python 3.13 venv, FastAPI, PyTorch CPU,${NC}"
    echo -e "  ${DIM}Playwright, Node.js 22, Redis, ffmpeg, SQLite3${NC}"
}

# ═══════════════════════════════════════════════════════════════════
#  INSTALL SCREEN 5 — System Packages
# ═══════════════════════════════════════════════════════════════════
install_system_packages() {
    new_screen 5
    echo -e "  ${BOLD}${WHITE}Phase 5/8${NC}  ${CYAN}System Packages${NC}"
    echo ""

    if [[ "$OS_TYPE" == "Darwin" ]]; then
        # ── macOS: Homebrew ──────────────────────────────────────
        if ! command -v brew &>/dev/null; then
            info "Installing Homebrew..."
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" </dev/null
            eval "$(/opt/homebrew/bin/brew shellenv 2>/dev/null || /usr/local/bin/brew shellenv 2>/dev/null)"
            ok "Homebrew installed"
        else
            ok "Homebrew: $(brew --version | head -1)"
        fi

        info "Installing core dependencies..."
        local brew_pkgs=(python@3.13 git curl wget jq sqlite ffmpeg htop cmake)
        local brew_total=${#brew_pkgs[@]}
        local brew_i=0
        for pkg in "${brew_pkgs[@]}"; do
            brew_i=$((brew_i + 1))
            if brew list --formula 2>/dev/null | grep -qx "$pkg"; then
                ok "  $pkg (already installed) [$brew_i/$brew_total]"
            else
                run_with_spin "Installing $pkg... [$brew_i/$brew_total]" brew install "$pkg" || true
                ok "  $pkg"
            fi
        done
        ok "Core packages (brew)"

        info "Installing Redis..."
        run_with_spin "Installing Redis..." brew install redis || true
        brew services start redis 2>/dev/null || true
        if redis-cli ping 2>/dev/null | grep -q PONG; then ok "Redis: running (PONG)"
        else warn "Redis: installed but not responding"; fi

        info "Installing security tools..."
        run_with_spin "Installing ClamAV..." brew install clamav || true
        ok "Security: ClamAV (chkrootkit/rkhunter skipped on macOS)"
    else
        # ── Linux: apt ───────────────────────────────────────────
        info "Updating package lists..."
        sudo apt update -y -qq 2>&1 | tail -1
        ok "Package lists updated"

        info "Upgrading system packages..."
        sudo apt upgrade -y -qq 2>&1 | tail -1
        ok "System upgraded"

        info "Installing core dependencies..."
        run_with_spin "apt: core packages..." \
            sudo apt install -y -qq \
            python3 python3-venv python3-pip \
            git curl wget jq build-essential sqlite3 ffmpeg \
            htop tmux ca-certificates gnupg || true
        ok "Core packages installed"

        info "Installing Redis..."
        sudo apt install -y -qq redis-tools redis-server 2>&1 | tail -1
        sudo systemctl enable --now redis-server 2>/dev/null || true
        if redis-cli ping 2>/dev/null | grep -q PONG; then ok "Redis: running (PONG)"
        else warn "Redis: installed but not responding"; fi

        info "Installing security audit tools..."
        run_with_spin "apt: security tools..." \
            sudo apt install -y -qq clamav clamav-daemon chkrootkit rkhunter || true
        sudo systemctl stop clamav-freshclam 2>/dev/null || true
        sudo freshclam 2>/dev/null || warn "ClamAV definitions update failed"
        sudo systemctl start clamav-freshclam 2>/dev/null || true
        ok "Security: ClamAV, chkrootkit, rkhunter"
    fi

    save_state 5
}

# ═══════════════════════════════════════════════════════════════════
#  INSTALL SCREEN 6 — Node.js, Claude CLI, Project Structure
# ═══════════════════════════════════════════════════════════════════
install_node_and_structure() {
    new_screen 6
    echo -e "  ${BOLD}${WHITE}Phase 6/8${NC}  ${CYAN}Node.js, Claude Code & Project Structure${NC}"
    echo ""

    if command -v node &>/dev/null; then
        local node_ver=$(node --version)
        local node_major="${node_ver#v}"
        node_major="${node_major%%.*}"
        if (( node_major >= 22 )); then ok "Node.js: $node_ver"
        else
            info "Upgrading Node.js to v22..."
            if [[ "$OS_TYPE" == "Darwin" ]]; then
                brew install node@22 2>&1 | tail -3
            else
                curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash - 2>&1 | tail -3
                sudo apt install -y -qq nodejs 2>&1 | tail -1
            fi
            ok "Node.js: $(node --version)"
        fi
    else
        info "Installing Node.js 22..."
        if [[ "$OS_TYPE" == "Darwin" ]]; then
            brew install node@22 2>&1 | tail -3
        else
            curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash - 2>&1 | tail -3
            sudo apt install -y -qq nodejs 2>&1 | tail -1
        fi
        ok "Node.js: $(node --version)"
    fi

    if command -v npm &>/dev/null; then ok "npm: $(npm --version)"
    else fail "npm not found"; exit 1; fi

    if command -v claude &>/dev/null; then ok "Claude Code CLI: already installed"
    else
        info "Installing Claude Code CLI..."
        if [[ "$OS_TYPE" == "Darwin" ]]; then
            npm install -g @anthropic-ai/claude-code 2>&1 | tail -3
        else
            sudo npm install -g @anthropic-ai/claude-code 2>&1 | tail -3
        fi
        if command -v claude &>/dev/null; then ok "Claude Code CLI: installed"
        else fail "Claude Code CLI installation failed"; exit 1; fi
    fi

    info "Creating directory tree..."
    if [[ "$OS_TYPE" == "Darwin" ]]; then
        mkdir -p "$KOVO_DIR"
    else
        sudo mkdir -p "$KOVO_DIR"
        sudo chown "$USER:$USER" "$KOVO_DIR"
    fi
    mkdir -p "$KOVO_DIR"/{src,config,scripts,scripts/experiments,tests,logs,systemd,assets}
    mkdir -p "$KOVO_DIR"/data/{tmp,audio,photos,documents,images,screenshots,backups}
    touch "$KOVO_DIR/data/kovo.db"
    mkdir -p "$WORKSPACE"/{memory/archive,skills,checklists,docs,agents}
    mkdir -p "$WORKSPACE/skills"/{report-builder/templates,security-audit,server-health,google-workspace,browser,phone-call}
    mkdir -p "$KOVO_DIR/.claude"
    mkdir -p "$KOVO_DIR/src/dashboard/frontend"
    ok "Directory tree ($(find "$KOVO_DIR" -type d | wc -l) dirs)"

    info "Cloning KOVO source..."
    if [ -d "$KOVO_DIR/src/gateway" ] && [ -f "$KOVO_DIR/src/gateway/main.py" ]; then
        git -C "$KOVO_DIR" pull origin main 2>/dev/null || warn "Git pull failed — using existing"
        ok "Source code up to date"
    else
        if run_with_spin "Cloning from GitHub..." git clone "$KOVO_REPO" "$KOVO_DIR/repo-tmp"; then
            # Copy source (use /* to avoid nested src/src/)
            cp -r "$KOVO_DIR/repo-tmp/src/"* "$KOVO_DIR/src/" 2>/dev/null || true
            # Copy ALL scripts from repo (update.sh, restore.sh, backup.sh, etc.)
            cp -r "$KOVO_DIR/repo-tmp/scripts/"* "$KOVO_DIR/scripts/" 2>/dev/null || true
            chmod +x "$KOVO_DIR/scripts/"*.sh 2>/dev/null || true
            # Copy requirements.txt for pip install -r
            [ -f "$KOVO_DIR/repo-tmp/requirements.txt" ] && cp "$KOVO_DIR/repo-tmp/requirements.txt" "$KOVO_DIR/requirements.txt"
            # Copy docs and assets
            [ -f "$KOVO_DIR/repo-tmp/CLAUDE.md" ] && cp "$KOVO_DIR/repo-tmp/CLAUDE.md" "$KOVO_DIR/CLAUDE.md"
            [ -f "$KOVO_DIR/repo-tmp/DOCS.md" ] && cp "$KOVO_DIR/repo-tmp/DOCS.md" "$KOVO_DIR/DOCS.md"
            [ -f "$KOVO_DIR/repo-tmp/README.md" ] && cp "$KOVO_DIR/repo-tmp/README.md" "$KOVO_DIR/README.md"
            [ -d "$KOVO_DIR/repo-tmp/assets" ] && cp -r "$KOVO_DIR/repo-tmp/assets/"* "$KOVO_DIR/assets/" 2>/dev/null
            rm -rf "$KOVO_DIR/repo-tmp"
            ok "Source cloned (src/, scripts/, requirements.txt, docs)"
        else warn "Git clone failed — will be built by Claude Code later"; fi
    fi

    if [[ "$OS_TYPE" != "Darwin" ]]; then
        echo "$USER ALL=(ALL) NOPASSWD: ALL" | sudo tee /etc/sudoers.d/kovo > /dev/null
        sudo chmod 440 /etc/sudoers.d/kovo
        ok "Sudo NOPASSWD for $USER"
    else
        ok "Sudo: not needed on macOS (user-owned install)"
    fi

    save_state 6
}

# ═══════════════════════════════════════════════════════════════════
#  INSTALL SCREEN 7 — Python Environment
# ═══════════════════════════════════════════════════════════════════
install_python_env() {
    new_screen 7
    echo -e "  ${BOLD}${WHITE}Phase 7/8${NC}  ${CYAN}Python Environment${NC}"
    echo ""

    info "Creating virtual environment..."
    if [[ "$OS_TYPE" == "Darwin" ]]; then
        # Use brew python3.13 explicitly (macOS system python is older)
        local brew_py="$(brew --prefix python@3.13 2>/dev/null)/bin/python3.13"
        if [[ -x "$brew_py" ]]; then
            "$brew_py" -m venv "$VENV"
            ok "venv uses brew Python 3.13"
        else
            # Fallback: try python3.13 in PATH, then any python3
            if command -v python3.13 &>/dev/null; then
                python3.13 -m venv "$VENV"
            else
                python3 -m venv "$VENV"
                warn "Using system Python ($(python3 --version)) — 3.13+ recommended"
            fi
        fi
    else
        python3 -m venv "$VENV"
    fi
    source "$VENV/bin/activate"
    pip install --upgrade pip -q 2>&1 | tail -1
    ok "venv at $VENV"

    # ── Group 1: Framework + API (fast, pure-python) ────────────
    progress_bar 1 7
    info "Installing web framework..."
    run_with_spin "pip: FastAPI + uvicorn + httpx..." \
        pip install -q fastapi "uvicorn[standard]" httpx pydantic python-dotenv PyYAML python-multipart
    ok "FastAPI + dependencies"

    # ── Group 2: Telegram + Google + GitHub ───────────────────
    progress_bar 2 7
    info "Installing integrations..."
    run_with_spin "pip: Telegram + Google + GitHub..." \
        pip install -q "python-telegram-bot[webhooks]" pyrogram tgcrypto edge-tts \
        google-api-python-client google-auth-httplib2 google-auth-oauthlib PyGithub
    ok "Telegram + Google + GitHub"

    # ── Group 3: Tools + testing ──────────────────────────────
    progress_bar 3 7
    info "Installing tools..."
    run_with_spin "pip: scheduler + psutil + testing..." \
        pip install -q apscheduler psutil pytest pytest-asyncio Pillow ddgs beautifulsoup4
    ok "Scheduler + tools + testing"

    # ── Group 4: Voice calls (optional, may fail on macOS) ────
    progress_bar 4 7
    info "Installing voice call support..."
    if run_with_spin "pip: py-tgcalls..." pip install -q py-tgcalls 2>/dev/null; then
        ok "py-tgcalls"
    else
        warn "py-tgcalls failed to build (voice calls disabled — other features unaffected)"
    fi

    # ── Group 5: PyTorch (optional on macOS) ──────────────────
    progress_bar 5 7
    info "Installing PyTorch..."
    if [[ "$OS_TYPE" == "Darwin" ]]; then
        if run_with_spin "pip: PyTorch..." pip install -q torch 2>/dev/null; then
            ok "PyTorch"
        else
            warn "PyTorch not available for this Python version (Groq transcription still works)"
        fi
    else
        run_with_spin "pip: PyTorch CPU..." pip install -q torch --index-url https://download.pytorch.org/whl/cpu
        ok "PyTorch CPU-only"
    fi

    # ── Group 6: Whisper (optional, depends on PyTorch) ───────
    progress_bar 6 7
    info "Installing Whisper..."
    if run_with_spin "pip: Whisper..." pip install -q openai-whisper --no-deps 2>/dev/null; then
        pip install -q tiktoken more-itertools numba tqdm numpy regex 2>/dev/null || true
        ok "Whisper"
    else
        warn "Whisper not available (Groq API transcription still works)"
    fi

    # ── Group 7: Playwright + Chromium ────────────────────────
    progress_bar 7 7
    info "Installing Playwright + Chromium..."
    run_with_spin "pip: Playwright..." pip install -q playwright
    run_with_spin "Downloading Chromium..." "$VENV/bin/playwright" install chromium
    if [[ "$OS_TYPE" != "Darwin" ]]; then
        "$VENV/bin/playwright" install-deps chromium 2>&1 | tail -2
    fi
    ok "Playwright + Chromium"

    # ── requirements.txt (extra deps from repo) ──────────────
    if [ -f "$KOVO_DIR/requirements.txt" ]; then
        run_with_spin "pip: requirements.txt..." "$VENV/bin/pip" install -r "$KOVO_DIR/requirements.txt" -q || true
        ok "requirements.txt"
    fi
    echo ""
    ok "Python environment complete"

    info "Downloading KOVO mascot..."
    if curl -sfL "$MASCOT_URL" -o "$KOVO_DIR/assets/kovo-mascot.png" 2>/dev/null; then
        echo ""
        show_mascot "$KOVO_DIR/assets/kovo-mascot.png" 2>/dev/null || true
        echo ""
        ok "Mascot rendered"
    elif [ -f "$KOVO_DIR/assets/kovo-mascot.png" ]; then
        echo ""
        show_mascot "$KOVO_DIR/assets/kovo-mascot.png" 2>/dev/null || true
        echo ""
    else dim "Mascot not available (cosmetic only)"; fi

    save_state 7
}

# ═══════════════════════════════════════════════════════════════════
#  INSTALL SCREEN 8 — Config, Skills, Verify, Done
# ═══════════════════════════════════════════════════════════════════
install_configs_and_finish() {
    new_screen 8
    echo -e "  ${BOLD}${WHITE}Phase 8/8${NC}  ${CYAN}Configuration, Skills & Verification${NC}"
    echo ""

    # ── Claude Code permissions ──────────────────────────────────
    info "Claude Code permissions..."
    cat > "$KOVO_DIR/.claude/settings.local.json" << EOF
{
  "permissions": {
    "allow": [
      "Bash($KOVO_DIR/venv/bin/pip *)", "Bash($KOVO_DIR/venv/bin/playwright *)",
      "Bash($KOVO_DIR/venv/bin/python *)", "Bash(apt *)", "Bash(cat *)",
      "Bash(cd *)", "Bash(chmod *)", "Bash(chown *)", "Bash(cp *)",
      "Bash(curl *)", "Bash(cut *)", "Bash(date *)", "Bash(df *)",
      "Bash(diff *)", "Bash(dirname *)", "Bash(docker *)", "Bash(du *)",
      "Bash(echo *)", "Bash(env *)", "Bash(ffmpeg *)", "Bash(find *)",
      "Bash(free *)", "Bash(gh *)", "Bash(grep *)", "Bash(head *)",
      "Bash(hostname *)", "Bash(id *)", "Bash(journalctl *)", "Bash(kill *)",
      "Bash(ln *)", "Bash(ls *)", "Bash(lsof *)", "Bash(mkdir *)",
      "Bash(mv *)", "Bash(node *)", "Bash(npm *)", "Bash(npx *)",
      "Bash(ps *)", "Bash(pwd)", "Bash(readlink *)", "Bash(redis-cli *)",
      "Bash(rm *)", "Bash(sed *)", "Bash(sort *)", "Bash(source *)",
      "Bash(sudo *)", "Bash(systemctl *)", "Bash(tail *)", "Bash(tar *)",
      "Bash(tee *)", "Bash(test *)", "Bash(touch *)", "Bash(tr *)",
      "Bash(uname *)", "Bash(uniq *)", "Bash(wc *)", "Bash(wget *)",
      "Bash(which *)", "Bash(whoami)", "Bash(xargs *)", "Edit(*)"
    ]
  }
}
EOF
    ok "Claude Code permissions (61 entries)"

    # ── settings.yaml ────────────────────────────────────────────
    info "settings.yaml..."
    cat > "$KOVO_DIR/config/settings.yaml.template" << SETTINGS_EOF
kovo:
  workspace: $KOVO_DIR/workspace
  data_dir: $KOVO_DIR/data
  log_dir: $KOVO_DIR/logs
telegram:
  token: \${TELEGRAM_BOT_TOKEN}
  allowed_users:
    - \${OWNER_TELEGRAM_ID}
ollama:
  url: http://<OLLAMA-HOST>:11434
  default_model: llama3.1:8b
  enabled: false
claude:
  default_model: sonnet
  memory_flush_model: sonnet
  timeout: 300
telegram_call:
  api_id: \${TELEGRAM_API_ID}
  api_hash: \${TELEGRAM_API_HASH}
  session_name: kovo_caller
  owner_user_id: \${OWNER_TELEGRAM_ID}
  call_timeout: 30
  tts:
    backend: edge-tts
    voice: en-US-AvaMultilingualNeural
google:
  credentials_file: $KOVO_DIR/config/google-credentials.json
  scopes:
    - https://www.googleapis.com/auth/drive
    - https://www.googleapis.com/auth/documents
    - https://www.googleapis.com/auth/gmail.modify
    - https://www.googleapis.com/auth/calendar
    - https://www.googleapis.com/auth/spreadsheets
heartbeat:
  enabled: false
  quick_interval: 30
  full_interval: 6
  morning_time: "08:00"
  use_ollama: false
security_audit:
  enabled: true
  schedule: "sun 07:00"   # weekly security scan
  tools:
    - clamav
    - chkrootkit
    - rkhunter
transcription:
  groq_api_key: \${GROQ_API_KEY}
  whisper_model: base
dashboard:
  port: $DASHBOARD_PORT
  host: 0.0.0.0
gateway:
  port: $GATEWAY_PORT
  host: 0.0.0.0
memory:
  auto_extract:
    enabled: true
    confidence_threshold: 0.7
    max_memories_per_extraction: 20
    extraction_input_token_cap: 4000
    consolidation_schedule: "sunday_3am"
    budget_max_lines: 500
    archive_after_days: 90
    model: sonnet
  structured_store:
    db_path: $KOVO_DIR/data/kovo.db
    max_db_size_mb: 100
    custom_table_prefix: "user_"
    schema_in_prompt: "on_demand"
SETTINGS_EOF
    ok "settings.yaml.template"

    # Copy template to live file (first install only — never overwrite user config)
    if [[ ! -f "$KOVO_DIR/config/settings.yaml" ]]; then
        cp "$KOVO_DIR/config/settings.yaml.template" "$KOVO_DIR/config/settings.yaml"
        ok "settings.yaml (from template)"
    else
        ok "settings.yaml preserved (existing config)"
    fi

    # ── .env ─────────────────────────────────────────────────────
    cat > "$KOVO_DIR/config/.env.template" << ENV_EOF
TELEGRAM_BOT_TOKEN=
OWNER_TELEGRAM_ID=
TELEGRAM_API_ID=
TELEGRAM_API_HASH=
CLAUDE_CODE_OAUTH_TOKEN=
GROQ_API_KEY=
GITHUB_TOKEN=
GOOGLE_CREDENTIALS_PATH=$KOVO_DIR/config/google-credentials.json
ENV_EOF
    if [[ ! -f "$KOVO_DIR/config/.env" ]]; then
        cp "$KOVO_DIR/config/.env.template" "$KOVO_DIR/config/.env"
        ok ".env created"
    else ok ".env preserved"; fi

    chmod 700 "$KOVO_DIR/config"
    chmod 600 "$KOVO_DIR/config/.env.template" "$KOVO_DIR/config/.env"
    chmod 600 "$KOVO_DIR/.claude/settings.local.json"
    [[ -f "$KOVO_DIR/data/kovo.db" ]] && chmod 600 "$KOVO_DIR/data/kovo.db"
    ok "Permissions secured"

    # ── Workspace ────────────────────────────────────────────────
    info "Copying workspace templates..."
    # Copy .template files to live files (first install only)
    for tmpl in "$WORKSPACE"/*.md.template; do
        [ -f "$tmpl" ] || continue
        live="${tmpl%.template}"
        if [[ ! -f "$live" ]]; then
            cp "$tmpl" "$live"
            ok "template → live: $(basename "$live")"
        fi
    done

        info "Workspace files..."
    [[ ! -f "$WORKSPACE/SOUL.md" ]] && printf "# SOUL.md\n## UNCONFIGURED\nSend any message on Telegram to start onboarding.\n" > "$WORKSPACE/SOUL.md"
    [[ ! -f "$WORKSPACE/USER.md" ]] && printf "# USER.md\n## UNCONFIGURED\n" > "$WORKSPACE/USER.md"
    [[ ! -f "$WORKSPACE/IDENTITY.md" ]] && printf "# IDENTITY.md\n## Name\nKovo\n## Creature Type\nBlue alien\n## UNCONFIGURED\n" > "$WORKSPACE/IDENTITY.md"
    [[ ! -f "$WORKSPACE/MEMORY.md" ]] && printf "# MEMORY.md\n\n## Preferences\n\n## Decisions\n\n## Facts\n\n## Projects\n\n## Action Items\n\n" > "$WORKSPACE/MEMORY.md"
    printf "# Sub-Agent Registry\n## Main Agent\n- **Name**: Kovo\n- **Tools**: all\n- **Status**: active\n## Sub-Agents\n*None yet.*\n" > "$WORKSPACE/AGENTS.md"
    printf "# HEARTBEAT.md\n## Every 30min (Ollama)\n- [ ] Disk/RAM/CPU checks\n## Every 6h (Claude)\n- [ ] Health report, memory review, auto-purge\n## Every morning 8am\n- [ ] Briefing, pending tasks\n## Every Sunday 7am\n- [ ] Security audit\n" > "$WORKSPACE/HEARTBEAT.md"
    ok "Workspace files"

    # ── 6 Skills ─────────────────────────────────────────────────
    info "Writing 6 skills..."
    for s in server-health google-workspace browser phone-call; do mkdir -p "$WORKSPACE/skills/$s"; done

    cat > "$WORKSPACE/skills/server-health/SKILL.md" << 'EOF'
---
name: server-health
description: Quick server health check — CPU, RAM, disk, services, connectivity.
tools: [shell]
trigger: health, status, server, check, system, cpu, ram, disk, uptime, load
---
# Server Health Skill
Quick checks: CPU load, RAM, disk, services, connectivity.
EOF

    cat > "$WORKSPACE/skills/google-workspace/SKILL.md" << 'EOF'
---
name: google-workspace
description: Google Docs, Drive, Gmail, Calendar, Sheets integration.
tools: [shell, google_api]
trigger: google, docs, drive, gmail, email, calendar, sheets
---
# Google Workspace Skill
Run /auth_google in Telegram to authenticate.
EOF

    cat > "$WORKSPACE/skills/browser/SKILL.md" << 'EOF'
---
name: browser
description: Web browsing, scraping, screenshots using Playwright.
tools: [shell, browser]
trigger: browse, website, screenshot, scrape, web, page, url
---
# Browser Skill
Headless Chromium for scraping, screenshots, form automation.
EOF

    cat > "$WORKSPACE/skills/phone-call/SKILL.md" << 'EOF'
---
name: phone-call
description: Telegram voice calls using Pyrogram userbot with TTS.
tools: [shell, telegram_call, tts]
trigger: call, phone, voice call, ring, urgent, emergency
---
# Phone Call Skill
/call message — falls back to voice message if not answered.
EOF

    [[ ! -f "$WORKSPACE/skills/report-builder/SKILL.md" ]] && printf -- "---\nname: report-builder\ndescription: Generate HTML reports — health, status, weekly.\ntools: [shell]\ntrigger: report, dashboard, health report, status page\n---\n# Report Builder\nSingle-file HTML with dark/light mode, charts, responsive layout.\n" > "$WORKSPACE/skills/report-builder/SKILL.md"
    [[ ! -f "$WORKSPACE/skills/security-audit/SKILL.md" ]] && printf -- "---\nname: security-audit\ndescription: Deep security audit — network, packages, users, malware.\ntools: [shell]\ntrigger: security, audit, scan, vulnerability, malware, rootkit\n---\n# Security Audit\nBaseline at $KOVO_DIR/data/security_baseline.json (path varies by OS). Schedule: Sunday 7am.\n" > "$WORKSPACE/skills/security-audit/SKILL.md"
    ok "6 skills"

    # ── TOOLS.md ─────────────────────────────────────────────────
    [[ ! -f "$WORKSPACE/TOOLS.md" ]] && cat > "$WORKSPACE/TOOLS.md" << 'EOF'
---
tools:
- { name: shell, status: configured, description: "Execute shell commands" }
- { name: browser, status: configured, description: "Playwright headless Chromium" }
- { name: tts, status: configured, description: "Text-to-speech (edge-tts)" }
- { name: ollama, status: not_configured, description: "Local LLM", config_needed: "Set host in dashboard" }
- { name: claude_cli, status: not_configured, description: "Claude Code CLI", config_needed: "Run claude login" }
- { name: whisper, status: not_configured, description: "Voice transcription", config_needed: "Set GROQ_API_KEY" }
- { name: telegram_call, status: not_configured, description: "Voice calls", config_needed: "Set API_ID/HASH" }
- { name: google_api, status: not_configured, description: "Google Workspace", config_needed: "Run /auth_google" }
- { name: github, status: not_configured, description: "GitHub integration", config_needed: "Set GITHUB_TOKEN" }
---
# Tool Registry
EOF
    ok "TOOLS.md (9 tools)"

    # ── Scripts ──────────────────────────────────────────────────
    cat > "$KOVO_DIR/scripts/backup.sh" << BKEOF
#!/bin/bash
SCRIPT_DIR="\$(cd "\$(dirname "\$0")" && pwd)"
KOVO_DIR="\${KOVO_DIR:-\$(cd "\$SCRIPT_DIR/.." && pwd)}"
D="\$KOVO_DIR/data/backups"; mkdir -p "\$D"
tar czf "\$D/workspace_\$(date +%Y%m%d).tar.gz" -C "\$KOVO_DIR" workspace/
find "\$D" -name "workspace_*.tar.gz" -mtime +30 -delete
echo "✓ Backup: \$D/workspace_\$(date +%Y%m%d).tar.gz"
BKEOF
    chmod +x "$KOVO_DIR/scripts/backup.sh"

    cat > "$KOVO_DIR/scripts/health-check.sh" << HCEOF
#!/bin/bash
SCRIPT_DIR="\$(cd "\$(dirname "\$0")" && pwd)"
KOVO_DIR="\${KOVO_DIR:-\$(cd "\$SCRIPT_DIR/.." && pwd)}"
G='\033[38;5;114m' R='\033[38;5;203m' B='\033[38;5;75m' N='\033[0m' DM='\033[2m'
echo -e "\n\${B}KOVO Health Check\${N} \${DM}\$(date '+%Y-%m-%d %H:%M')\${N}\n"
c() { if eval "\$2" &>/dev/null; then echo -e "  \${G}✓\${N} \$1"; else echo -e "  \${R}✗\${N} \$1"; fi; }
if [[ "\$(uname)" == "Darwin" ]]; then
    c "KOVO service" "launchctl list com.kovo.agent 2>/dev/null | grep -q PID"
else
    c "KOVO service" "systemctl is-active --quiet kovo"
fi
c "Redis" "redis-cli ping | grep -q PONG"
c "Python venv" "[ -f \$KOVO_DIR/venv/bin/python ]"
c "Claude CLI" "command -v claude"
echo ""
HCEOF
    chmod +x "$KOVO_DIR/scripts/health-check.sh"
    ok "Scripts: backup.sh, health-check.sh"

    # ── Logrotate + CLAUDE.md ────────────────────────────────────
    if [[ "$OS_TYPE" != "Darwin" ]]; then
        [[ ! -f /etc/logrotate.d/kovo ]] && sudo tee /etc/logrotate.d/kovo > /dev/null << 'EOF'
/opt/kovo/logs/gateway.log { daily rotate 7 compress missingok notifempty copytruncate }
EOF
    fi
    if [[ -f /tmp/CLAUDE.md ]]; then cp /tmp/CLAUDE.md "$KOVO_DIR/CLAUDE.md"; ok "CLAUDE.md"
    elif [[ -f "$KOVO_DIR/CLAUDE.md" ]]; then ok "CLAUDE.md exists"
    else warn "CLAUDE.md not found"; fi

    # ── Service (systemd on Linux, launchd on macOS) ────────────
    if [[ "$OS_TYPE" == "Darwin" ]]; then
        info "LaunchAgent service..."
        mkdir -p "$KOVO_DIR/launchd"
        mkdir -p ~/Library/LaunchAgents

        # Build .env as environment dict for plist
        local env_args=""
        if [[ -f "$KOVO_DIR/config/.env" ]]; then
            while IFS='=' read -r key value; do
                [[ -z "$key" || "$key" == \#* ]] && continue
                value="${value%%\#*}"  # strip inline comments
                value="$(echo "$value" | xargs)"  # trim whitespace
                [[ -n "$value" ]] && env_args+="            <key>$key</key>\n            <string>$value</string>\n"
            done < "$KOVO_DIR/config/.env"
        fi

        cat > "$KOVO_DIR/launchd/com.kovo.agent.plist" << PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.kovo.agent</string>
    <key>ProgramArguments</key>
    <array>
        <string>$KOVO_DIR/venv/bin/python</string>
        <string>-m</string>
        <string>uvicorn</string>
        <string>src.gateway.main:app</string>
        <string>--host</string>
        <string>0.0.0.0</string>
        <string>--port</string>
        <string>$GATEWAY_PORT</string>
        <string>--log-level</string>
        <string>info</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$KOVO_DIR</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$KOVO_DIR/logs/gateway.log</string>
    <key>StandardErrorPath</key>
    <string>$KOVO_DIR/logs/gateway.log</string>
</dict>
</plist>
PLISTEOF
        cp "$KOVO_DIR/launchd/com.kovo.agent.plist" ~/Library/LaunchAgents/com.kovo.agent.plist
        ok "com.kovo.agent.plist"
    else
        info "Systemd service..."
        cat > "$KOVO_DIR/systemd/kovo.service" << SVCEOF
[Unit]
Description=KOVO AI Agent
After=network.target redis.service
Wants=redis.service
[Service]
Type=simple
User=${USER}
WorkingDirectory=$KOVO_DIR
EnvironmentFile=$KOVO_DIR/config/.env
ExecStart=$KOVO_DIR/venv/bin/python -m uvicorn src.gateway.main:app --host 0.0.0.0 --port $GATEWAY_PORT --log-level info
Restart=always
RestartSec=5
TimeoutStopSec=30
StandardOutput=append:$KOVO_DIR/logs/gateway.log
StandardError=append:$KOVO_DIR/logs/gateway.log
[Install]
WantedBy=multi-user.target
SVCEOF
        sudo cp "$KOVO_DIR/systemd/kovo.service" /etc/systemd/system/kovo.service
        sudo systemctl daemon-reload
        ok "kovo.service"
    fi

    # ── Verification ─────────────────────────────────────────────
    echo ""
    echo -e "  ${BOLD}${WHITE}Verification${NC}"
    echo ""
    local passed=0 failed=0 opt_passed=0 opt_failed=0
    v() { if eval "$2" &>/dev/null; then ok "$1"; passed=$((passed+1)); else fail "$1"; failed=$((failed+1)); fi }
    o() { if eval "$2" &>/dev/null; then ok "$1"; opt_passed=$((opt_passed+1)); else warn "$1 (optional)"; opt_failed=$((opt_failed+1)); fi }

    echo -e "  ${WHITE}Required:${NC}"
    v "Python 3.11+"     "$VENV/bin/python --version | grep -qE '3\.1[1-9]'"
    v "Node.js 22+"      "node --version | grep -qE 'v2[2-9]'"
    v "Claude CLI"       "command -v claude"
    v "venv"             "[ -f $VENV/bin/python ]"
    v "FastAPI"          "$VENV/bin/python -c 'import fastapi'"
    v "python-multipart" "$VENV/bin/python -c 'import multipart'"
    v "Telegram"         "$VENV/bin/python -c 'import telegram'"
    v "Playwright"       "$VENV/bin/python -c 'import playwright'"
    v "Pillow"           "$VENV/bin/python -c 'import PIL'"
    v "ffmpeg"           "command -v ffmpeg"
    v "SOUL.md"          "[ -f $WORKSPACE/SOUL.md ]"
    v "settings.yaml"    "[ -f $KOVO_DIR/config/settings.yaml ]"
    v "scripts"          "[ -f $KOVO_DIR/scripts/update.sh ]"
    if [[ "$OS_TYPE" == "Darwin" ]]; then
        v "launchd"        "[ -f ~/Library/LaunchAgents/com.kovo.agent.plist ]"
    else
        v "systemd"          "[ -f /etc/systemd/system/kovo.service ]"
    fi
    v "6 skills"         "[ $(find $WORKSPACE/skills -name SKILL.md | wc -l) -ge 6 ]"

    echo ""
    echo -e "  ${WHITE}Optional:${NC}"
    o "Redis"            "redis-cli ping 2>/dev/null | grep -q PONG"
    o "PyTorch"          "$VENV/bin/python -c 'import torch'"
    o "Whisper"          "$VENV/bin/python -c 'import whisper'"
    o "py-tgcalls"       "$VENV/bin/python -c 'import pytgcalls'"
    o "ClamAV"           "command -v clamscan"

    echo ""
    echo -e "  ${GREEN}${BOLD}$passed/$((passed+failed)) required passed${NC}"
    if (( opt_failed > 0 )); then
        echo -e "  ${YELLOW}$opt_passed/$((opt_passed+opt_failed)) optional passed${NC} ${DIM}(warnings above are non-blocking)${NC}"
    else
        echo -e "  ${GREEN}$opt_passed/$((opt_passed+opt_failed)) optional passed${NC}"
    fi

    # ── Dashboard Build ──────────────────────────────────────────
    local dash_dir="$KOVO_DIR/src/dashboard/frontend"
    if [ -d "$dash_dir" ] && [ -f "$dash_dir/package.json" ]; then
        info "Building dashboard..."
        # Fix npm cache permissions (may have root ownership from prior sudo npm)
        if [[ "$OS_TYPE" == "Darwin" ]] && [ -d "$HOME/.npm" ]; then
            chown -R "$(whoami)" "$HOME/.npm" 2>/dev/null || true
        fi
        cd "$dash_dir"
        run_with_spin "npm install..." npm install --silent || true
        if npm run build 2>/dev/null; then
            ok "Dashboard built"
        else
            warn "Dashboard build failed (can be built later with: cd $dash_dir && npm run build)"
        fi
        cd "$KOVO_DIR"
    else warn "Dashboard frontend not found — will be built by Claude Code"; fi

    clear_state
    save_state 8

    # ── DONE SCREEN ──────────────────────────────────────────────
    if [[ "$OS_TYPE" == "Darwin" ]]; then
        local vm_ip=$(ipconfig getifaddr en0 2>/dev/null || echo "localhost")
    else
        local vm_ip=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "your-ip")
    fi
    echo ""
    echo -e "  ${BLUE}${BOLD}╔══════════════════════════════════════════════════╗${NC}"
    echo -e "  ${BLUE}${BOLD}║           KOVO is installed!                     ║${NC}"
    echo -e "  ${BLUE}${BOLD}╚══════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  ${CYAN}1${NC} Open the dashboard to complete setup:"
    echo -e "     ${WHITE}http://${vm_ip}:${GATEWAY_PORT}/dashboard/setup${NC}"
    echo ""
    echo -e "  ${CYAN}2${NC} The setup wizard walks you through:"
    echo -e "     ${DIM}• Telegram bot token + user ID${NC}"
    echo -e "     ${DIM}• Owner name + LLM preferences${NC}"
    echo -e "     ${DIM}• Optional: Groq, GitHub, Google${NC}"
    echo -e "     ${DIM}• Build + start the service${NC}"
    echo ""
    echo -e "  ${WHITE}Quick commands:${NC}"
    echo -e "  ${DIM}$KOVO_DIR/scripts/health-check.sh${NC}  ${GRAY}status${NC}"
    echo -e "  ${DIM}$KOVO_DIR/scripts/backup.sh${NC}        ${GRAY}backup${NC}"
    if [[ "$OS_TYPE" == "Darwin" ]]; then
        echo -e "  ${DIM}tail -f $KOVO_DIR/logs/gateway.log${NC}  ${GRAY}logs${NC}"
    else
        echo -e "  ${DIM}sudo journalctl -fu kovo${NC}           ${GRAY}logs${NC}"
    fi
    echo ""
}

# ═══════════════════════════════════════════════════════════════════
#  MAIN — Wizard Loop + Sequential Install
# ═══════════════════════════════════════════════════════════════════
main() {
    local start=0
    if $RESUME; then
        start=$(load_state)
        if (( start > 0 )); then
            new_screen
            info "Resuming from phase $((start+1))..."
            if [[ -f "$KOVO_DIR/config/settings.yaml" ]]; then
                GATEWAY_PORT=$(grep -A1 'gateway:' "$KOVO_DIR/config/settings.yaml" 2>/dev/null | grep 'port:' | awk '{print $2}' || echo "8080")
                DASHBOARD_PORT=$(grep -A1 'dashboard:' "$KOVO_DIR/config/settings.yaml" 2>/dev/null | grep 'port:' | awk '{print $2}' || echo "3000")
            fi
            sleep 1
        fi
    fi

    # ── Wizard phases 1-4 (can go back) ──────────────────────────
    if (( start < 4 )); then
        local wiz=$((start < 1 ? 1 : start + 1))
        (( wiz > 4 )) && wiz=4
        while (( wiz <= 4 )); do
            case $wiz in
                1) screen_welcome ;;
                2) screen_claude_auth ;;
                3) screen_network ;;
                4) screen_overview ;;
            esac
            if wizard_nav $wiz; then
                wiz=$((wiz + 1))
            else
                (( wiz > 1 )) && wiz=$((wiz - 1))
            fi
        done
        save_state 4
    fi

    # ── Install phases 5-8 (one direction) ───────────────────────
    (( start < 5 )) && install_system_packages
    (( start < 6 )) && install_node_and_structure
    (( start < 7 )) && install_python_env
    (( start < 8 )) && install_configs_and_finish

    trap - EXIT
}

main
