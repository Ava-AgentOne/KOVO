#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# KOVO — Self-Hosted AI Agent Installer v5.0
# https://github.com/Ava-AgentOne/kovo
#
# A beautiful, interactive installer for KOVO — your personal
# AI agent powered by Claude Code CLI.
#
# Usage:
#   bash bootstrap.sh              # Interactive mode (recommended)
#   bash bootstrap.sh --resume     # Resume a failed/interrupted install
#   bash bootstrap.sh --yes        # Auto-accept all prompts
#   bash bootstrap.sh --uninstall  # Clean removal
#
# Requirements: Ubuntu 24.04+ · 8GB+ RAM · 30GB+ free disk
# License: GNU AGPLv3
# ═══════════════════════════════════════════════════════════════════

set -euo pipefail

# ─── Versioning ───────────────────────────────────────────────────
INSTALLER_VERSION="5.0"
KOVO_DIR="/opt/kovo"
VENV="$KOVO_DIR/venv"
WORKSPACE="$KOVO_DIR/workspace"
STATE_FILE="/tmp/.kovo-install-state"
LOG_FILE="/tmp/kovo-install.log"
KOVO_REPO="https://github.com/Ava-AgentOne/kovo.git"
MASCOT_URL="https://raw.githubusercontent.com/Ava-AgentOne/kovo/main/assets/kovo-mascot.png"

# ─── Parse CLI flags ─────────────────────────────────────────────
RESUME=false
AUTO_YES=false
UNINSTALL=false
for arg in "$@"; do
    case "$arg" in
        --resume)    RESUME=true ;;
        --yes|-y)    AUTO_YES=true ;;
        --uninstall) UNINSTALL=true ;;
        --help|-h)
            echo "Usage: bash bootstrap.sh [--resume] [--yes] [--uninstall]"
            exit 0
            ;;
    esac
done

# ─── Terminal Colors & Helpers ────────────────────────────────────
if [[ -t 1 ]]; then
    BOLD='\033[1m'
    DIM='\033[2m'
    BLUE='\033[38;5;75m'
    CYAN='\033[38;5;80m'
    GREEN='\033[38;5;114m'
    YELLOW='\033[38;5;221m'
    RED='\033[38;5;203m'
    PINK='\033[38;5;211m'
    GRAY='\033[38;5;245m'
    WHITE='\033[38;5;255m'
    NC='\033[0m'
else
    BOLD='' DIM='' BLUE='' CYAN='' GREEN='' YELLOW='' RED='' PINK='' GRAY='' WHITE='' NC=''
fi

exec > >(tee -a "$LOG_FILE") 2>&1

ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
warn() { echo -e "  ${YELLOW}⚠${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1"; }
info() { echo -e "  ${BLUE}→${NC} $1"; }
dim()  { echo -e "  ${GRAY}$1${NC}"; }

phase_header() {
    local num="$1" total="$2" title="$3"
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "  ${BOLD}${WHITE}Phase $num/$total${NC}  ${CYAN}$title${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

progress_bar() {
    local current="$1" total="$2"
    local pct=$((current * 100 / total))
    local filled=$((pct / 2))
    local empty=$((50 - filled))
    local bar="${BLUE}"
    for ((i=0; i<filled; i++)); do bar+="█"; done
    bar+="${GRAY}"
    for ((i=0; i<empty; i++)); do bar+="░"; done
    bar+="${NC}"
    echo -e "  ${bar} ${WHITE}${pct}%${NC}"
}

confirm() {
    local prompt="$1"
    if $AUTO_YES; then return 0; fi
    echo -en "  ${PINK}?${NC} ${prompt} ${DIM}[Y/n]${NC}: "
    read -r answer
    [[ "${answer,,}" != "n" ]]
}

# ─── State Management (resume support) ───────────────────────────
save_state() { echo "$1" > "$STATE_FILE"; }
load_state() { [[ -f "$STATE_FILE" ]] && cat "$STATE_FILE" || echo "0"; }
clear_state() { rm -f "$STATE_FILE"; }

# ─── Error Handler ────────────────────────────────────────────────
trap_handler() {
    local exit_code=$?
    if [[ $exit_code -ne 0 ]]; then
        echo ""
        fail "Installation interrupted at phase $(load_state)."
        echo ""
        echo -e "  ${YELLOW}To resume from where you left off:${NC}"
        echo -e "    ${WHITE}bash bootstrap.sh --resume${NC}"
        echo ""
        echo -e "  ${GRAY}Full log: ${LOG_FILE}${NC}"
        echo ""
    fi
}
trap trap_handler EXIT

# ─── Mascot Display (truecolor block art from PNG) ───────────────
show_mascot() {
    local img_path="$1"
    # Use PIL to convert image to truecolor half-block art
    python3 << MASCOT_PYEOF
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

# ─── Simple Banner (before PIL is available) ─────────────────────
show_banner() {
    echo ""
    echo -e "${BLUE}${BOLD}"
    echo "   ██╗  ██╗ ██████╗ ██╗   ██╗ ██████╗ "
    echo "   ██║ ██╔╝██╔═══██╗██║   ██║██╔═══██╗"
    echo "   █████╔╝ ██║   ██║██║   ██║██║   ██║"
    echo "   ██╔═██╗ ██║   ██║╚██╗ ██╔╝██║   ██║"
    echo "   ██║  ██╗╚██████╔╝ ╚████╔╝ ╚██████╔╝"
    echo "   ╚═╝  ╚═╝ ╚═════╝   ╚═══╝   ╚═════╝ "
    echo -e "${NC}"
    echo -e "  ${BOLD}${WHITE}Self-Hosted AI Agent${NC}  ${GRAY}v${INSTALLER_VERSION} installer${NC}"
    echo -e "  ${DIM}Powered by Claude Code · GNU AGPLv3${NC}"
    echo -e "  ${DIM}github.com/Ava-AgentOne/kovo${NC}"
    echo ""
}

# ═══════════════════════════════════════════════════════════════════
#  UNINSTALL
# ═══════════════════════════════════════════════════════════════════
if $UNINSTALL; then
    show_banner
    echo -e "  ${RED}${BOLD}Uninstall KOVO${NC}"
    echo ""
    warn "This will remove KOVO and all its data from this system."
    if ! confirm "Are you sure?"; then echo "  Cancelled."; exit 0; fi
    echo ""
    info "Stopping service..."
    sudo systemctl stop kovo 2>/dev/null || true
    sudo systemctl disable kovo 2>/dev/null || true
    sudo rm -f /etc/systemd/system/kovo.service
    sudo systemctl daemon-reload
    info "Removing /opt/kovo..."
    sudo rm -rf "$KOVO_DIR"
    info "Cleaning up..."
    sudo rm -f /etc/sudoers.d/kovo /etc/logrotate.d/kovo
    echo ""
    ok "KOVO has been uninstalled."
    dim "Node.js, Python, Redis, and other system packages were left in place."
    echo ""
    exit 0
fi

# ═══════════════════════════════════════════════════════════════════
#  PHASE 1 — Pre-flight Checks
# ═══════════════════════════════════════════════════════════════════
preflight() {
    show_banner

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

    if ! confirm "Ready to begin?"; then echo "  Cancelled."; exit 0; fi

    phase_header "1" "8" "Pre-flight Checks"

    local errors=0

    # OS
    if [[ -f /etc/os-release ]]; then
        source /etc/os-release
        if [[ "$ID" == "ubuntu" ]]; then
            local ver_major="${VERSION_ID%%.*}"
            if (( ver_major >= 24 )); then ok "OS: $PRETTY_NAME"
            else warn "Ubuntu $VERSION_ID — 24.04+ recommended"; fi
        else warn "Non-Ubuntu OS ($ID) — tested on Ubuntu"; fi
    else fail "Cannot detect OS"; errors=$((errors+1)); fi

    # RAM
    local ram_mb=$(free -m | awk '/^Mem:/{print $2}')
    if (( ram_mb >= 7000 )); then ok "RAM: ${ram_mb}MB ($(( ram_mb / 1024 ))GB)"
    elif (( ram_mb >= 4000 )); then warn "RAM: ${ram_mb}MB — 8GB+ recommended"
    else fail "RAM: ${ram_mb}MB — minimum 4GB"; errors=$((errors+1)); fi

    # Disk
    local disk_gb=$(( $(df / --output=avail | tail -1 | tr -d ' ') / 1048576 ))
    if (( disk_gb >= 30 )); then ok "Disk: ${disk_gb}GB available"
    elif (( disk_gb >= 15 )); then warn "Disk: ${disk_gb}GB — 30GB+ recommended"
    else fail "Disk: ${disk_gb}GB — need 15GB+"; errors=$((errors+1)); fi

    # Internet
    if curl -sf --max-time 5 https://pypi.org > /dev/null 2>&1; then ok "Internet: connected"
    else fail "Internet: no connection"; errors=$((errors+1)); fi

    # Sudo
    if sudo -n true 2>/dev/null; then ok "Sudo: available"
    elif sudo true; then ok "Sudo: available"
    else fail "Sudo: not available"; errors=$((errors+1)); fi

    # Python
    if command -v python3 &>/dev/null; then ok "Python: $(python3 --version | cut -d' ' -f2)"
    else fail "Python3: not found"; errors=$((errors+1)); fi

    # Port checks
    if ! ss -tlnp | grep -q ':8080 ' 2>/dev/null; then ok "Port 8080: available"
    else warn "Port 8080: in use"; fi
    if ! ss -tlnp | grep -q ':3000 ' 2>/dev/null; then ok "Port 3000: available"
    else warn "Port 3000: in use"; fi

    # Existing install
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
    save_state 1
}

# ═══════════════════════════════════════════════════════════════════
#  PHASE 2 — Claude Code Authentication
# ═══════════════════════════════════════════════════════════════════
authenticate_claude() {
    phase_header "2" "8" "Claude Code Authentication"

    echo ""
    echo -e "  KOVO uses ${WHITE}Claude Code CLI${NC} as its brain. It runs Claude"
    echo -e "  as a subprocess (${DIM}claude -p${NC}) to handle complex tasks."
    echo ""
    echo -e "  This requires a ${WHITE}Claude Max${NC} or ${WHITE}Claude Team${NC} subscription."
    echo ""

    # Check if already authenticated
    if command -v claude &>/dev/null && claude --version &>/dev/null 2>&1; then
        # Try a quick auth check
        if claude api-key 2>/dev/null | grep -q "authenticated" 2>/dev/null; then
            ok "Claude Code: already authenticated"
            save_state 2
            return
        fi
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

    if ! confirm "Have you completed 'claude login'?"; then
        warn "Skipping auth — you can authenticate later with: claude login"
    else
        info "Verifying Claude Code authentication..."
        if command -v claude &>/dev/null; then
            ok "Claude Code CLI: installed"
            # Attempt to verify auth (best effort)
            local claude_ver=$(claude --version 2>/dev/null || echo "unknown")
            ok "Claude Code version: $claude_ver"
        else
            warn "Claude Code CLI not yet installed — will install in Phase 4"
        fi
    fi

    save_state 2
}

# ═══════════════════════════════════════════════════════════════════
#  PHASE 3 — Network Configuration
# ═══════════════════════════════════════════════════════════════════
GATEWAY_PORT="8080"
DASHBOARD_PORT="3000"

configure_network() {
    phase_header "3" "8" "Network Configuration"

    echo ""
    echo -e "  KOVO runs two web services on your VM:"
    echo ""
    echo -e "  ${WHITE}Gateway${NC} ${DIM}(default: 8080)${NC}"
    echo -e "    The main API server. Handles Telegram webhooks,"
    echo -e "    the chat WebSocket, and serves the production"
    echo -e "    dashboard. This is the port you'll access KOVO on."
    echo -e "    Example: ${CYAN}http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo 'your-ip'):8080${NC}"
    echo ""
    echo -e "  ${WHITE}Dashboard dev server${NC} ${DIM}(default: 3000)${NC}"
    echo -e "    Only used during development when editing the"
    echo -e "    React dashboard with hot-reload. Not needed for"
    echo -e "    normal use — the gateway serves the built dashboard."
    echo ""

    if confirm "Use default ports (8080 + 3000)?"; then
        GATEWAY_PORT="8080"
        DASHBOARD_PORT="3000"
    else
        echo -en "  ${PINK}?${NC} Gateway port ${DIM}[8080]${NC}: "
        read -r gp
        GATEWAY_PORT="${gp:-8080}"
        echo -en "  ${PINK}?${NC} Dashboard dev port ${DIM}[3000]${NC}: "
        read -r dp
        DASHBOARD_PORT="${dp:-3000}"
    fi

    ok "Gateway:   :${GATEWAY_PORT} → http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo 'your-ip'):${GATEWAY_PORT}"
    ok "Dashboard: :${DASHBOARD_PORT} → dev only"

    save_state 3
}

# ═══════════════════════════════════════════════════════════════════
#  PHASE 4 — Installation Overview + System Packages
# ═══════════════════════════════════════════════════════════════════
install_everything() {
    phase_header "4" "8" "Installation Overview"

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
    echo -e "  ${WHITE}Skills${NC} ${DIM}(6 default — KOVO learns procedures)${NC}"
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
    echo -e "  ${WHITE}Packages${NC} ${DIM}(highlights)${NC}"
    echo -e "    Python 3.13 venv, FastAPI, PyTorch CPU, Playwright,"
    echo -e "    Node.js 22, Redis, ffmpeg, SQLite3"
    echo ""

    if ! confirm "Proceed with installation?"; then echo "  Cancelled."; exit 0; fi

    # ── System packages ──────────────────────────────────────────
    phase_header "4" "8" "System Packages"

    info "Updating package lists..."
    sudo apt update -y -qq 2>&1 | tail -1
    ok "Package lists updated"

    info "Upgrading system packages..."
    sudo apt upgrade -y -qq 2>&1 | tail -1
    ok "System upgraded"

    info "Installing core dependencies..."
    sudo apt install -y -qq \
        python3 python3-venv python3-pip \
        git curl wget jq \
        build-essential sqlite3 ffmpeg \
        htop tmux ca-certificates gnupg \
        2>&1 | tail -1
    ok "Core packages installed"

    # Redis
    info "Installing Redis..."
    sudo apt install -y -qq redis-tools redis-server 2>&1 | tail -1
    sudo systemctl enable --now redis-server 2>/dev/null || true
    if redis-cli ping 2>/dev/null | grep -q PONG; then ok "Redis: running (PONG)"
    else warn "Redis: installed but not responding"; fi

    # Security tools (always included)
    info "Installing security audit tools..."
    sudo apt install -y -qq clamav clamav-daemon chkrootkit rkhunter 2>&1 | tail -1
    sudo systemctl stop clamav-freshclam 2>/dev/null || true
    sudo freshclam 2>/dev/null || warn "ClamAV definitions update failed"
    sudo systemctl start clamav-freshclam 2>/dev/null || true
    ok "Security: ClamAV, chkrootkit, rkhunter"

    save_state 4
}

# ═══════════════════════════════════════════════════════════════════
#  PHASE 5 — Node.js, Claude Code CLI, Project Structure
# ═══════════════════════════════════════════════════════════════════
setup_node_and_structure() {
    phase_header "5" "8" "Node.js, Claude Code & Project Structure"

    # Node.js 22
    if command -v node &>/dev/null; then
        local node_major="${$(node --version)#v}"
        node_major="${node_major%%.*}"
        if (( node_major >= 22 )); then ok "Node.js: $(node --version)"
        else
            info "Upgrading Node.js to v22..."
            curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash - 2>&1 | tail -3
            sudo apt install -y -qq nodejs 2>&1 | tail -1
            ok "Node.js: $(node --version)"
        fi
    else
        info "Installing Node.js 22..."
        curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash - 2>&1 | tail -3
        sudo apt install -y -qq nodejs 2>&1 | tail -1
        ok "Node.js: $(node --version)"
    fi

    if command -v npm &>/dev/null; then ok "npm: $(npm --version)"
    else fail "npm not found"; exit 1; fi

    # Claude Code CLI
    if command -v claude &>/dev/null; then
        ok "Claude Code CLI: already installed"
    else
        info "Installing Claude Code CLI..."
        sudo npm install -g @anthropic-ai/claude-code 2>&1 | tail -3
        if command -v claude &>/dev/null; then ok "Claude Code CLI: installed"
        else fail "Claude Code CLI installation failed"; exit 1; fi
    fi

    # Project structure
    info "Creating directory tree..."
    sudo mkdir -p "$KOVO_DIR"
    sudo chown "$USER:$USER" "$KOVO_DIR"

    mkdir -p "$KOVO_DIR"/{src,config,scripts,scripts/experiments,tests,logs,systemd,assets}
    mkdir -p "$KOVO_DIR"/data/{tmp,audio,photos,documents,images,screenshots,backups}
    touch "$KOVO_DIR/data/kovo.db"
    mkdir -p "$WORKSPACE"/{memory/archive,skills,checklists,docs,agents}
    mkdir -p "$WORKSPACE/skills"/{report-builder/templates,security-audit,server-health,google-workspace,browser,phone-call}
    mkdir -p "$KOVO_DIR/.claude"
    mkdir -p "$KOVO_DIR/src/dashboard/frontend"

    ok "Directory tree created ($(find "$KOVO_DIR" -type d | wc -l) directories)"

    # Clone source
    info "Cloning KOVO source..."
    if [ -d "$KOVO_DIR/src/gateway" ] && [ -f "$KOVO_DIR/src/gateway/main.py" ]; then
        git -C "$KOVO_DIR" pull origin main 2>/dev/null || warn "Git pull failed — using existing"
        ok "Source code up to date"
    else
        if git clone "$KOVO_REPO" "$KOVO_DIR/repo-tmp" 2>/dev/null; then
            cp -r "$KOVO_DIR/repo-tmp/src" "$KOVO_DIR/src" 2>/dev/null || true
            [ -f "$KOVO_DIR/repo-tmp/CLAUDE.md" ] && cp "$KOVO_DIR/repo-tmp/CLAUDE.md" "$KOVO_DIR/CLAUDE.md"
            [ -f "$KOVO_DIR/repo-tmp/DOCS.md" ] && cp "$KOVO_DIR/repo-tmp/DOCS.md" "$KOVO_DIR/DOCS.md"
            [ -d "$KOVO_DIR/repo-tmp/assets" ] && cp -r "$KOVO_DIR/repo-tmp/assets/"* "$KOVO_DIR/assets/" 2>/dev/null
            rm -rf "$KOVO_DIR/repo-tmp"
            ok "Source cloned from GitHub"
        else
            warn "Git clone failed — source will be built by Claude Code later"
        fi
    fi

    # Sudo NOPASSWD
    echo "$USER ALL=(ALL) NOPASSWD: ALL" | sudo tee /etc/sudoers.d/kovo > /dev/null
    sudo chmod 440 /etc/sudoers.d/kovo
    ok "Sudo NOPASSWD for $USER"

    save_state 5
}

# ═══════════════════════════════════════════════════════════════════
#  PHASE 6 — Python Environment
# ═══════════════════════════════════════════════════════════════════
install_python_env() {
    phase_header "6" "8" "Python Environment"

    info "Creating virtual environment..."
    python3 -m venv "$VENV"
    source "$VENV/bin/activate"
    pip install --upgrade pip -q 2>&1 | tail -1
    ok "venv at $VENV"

    progress_bar 1 5
    info "Installing core packages..."
    pip install -q \
        fastapi "uvicorn[standard]" "python-telegram-bot[webhooks]" \
        httpx pydantic python-dotenv PyYAML apscheduler psutil \
        pyrogram tgcrypto py-tgcalls edge-tts \
        google-api-python-client google-auth-httplib2 google-auth-oauthlib \
        PyGithub pytest pytest-asyncio Pillow
    ok "Core Python packages"

    progress_bar 2 5
    info "Installing PyTorch (CPU-only)..."
    pip install -q torch --index-url https://download.pytorch.org/whl/cpu
    ok "PyTorch CPU-only"

    progress_bar 3 5
    info "Installing Whisper..."
    pip install -q openai-whisper --no-deps
    pip install -q tiktoken more-itertools numba tqdm numpy regex
    ok "Whisper (no-GPU deps)"

    progress_bar 4 5
    info "Installing Playwright + Chromium..."
    pip install -q playwright
    "$VENV/bin/playwright" install chromium 2>&1 | tail -2
    "$VENV/bin/playwright" install-deps chromium 2>&1 | tail -2
    ok "Playwright + Chromium"

    # Install from requirements.txt if present
    if [ -f "$KOVO_DIR/requirements.txt" ]; then
        "$VENV/bin/pip" install -r "$KOVO_DIR/requirements.txt" -q
        ok "requirements.txt"
    fi

    progress_bar 5 5
    echo ""
    ok "Python environment complete"

    # Download mascot and display it
    info "Downloading KOVO mascot..."
    if curl -sfL "$MASCOT_URL" -o "$KOVO_DIR/assets/kovo-mascot.png" 2>/dev/null; then
        echo ""
        show_mascot "$KOVO_DIR/assets/kovo-mascot.png" 2>/dev/null || true
        echo ""
        ok "Mascot downloaded and rendered"
    elif [ -f "$KOVO_DIR/assets/kovo-mascot.png" ]; then
        echo ""
        show_mascot "$KOVO_DIR/assets/kovo-mascot.png" 2>/dev/null || true
        echo ""
        ok "Mascot rendered from local copy"
    else
        dim "Mascot not available (cosmetic only)"
    fi

    save_state 6
}

# ═══════════════════════════════════════════════════════════════════
#  PHASE 7 — Configuration, Workspace, Skills & Scripts
# ═══════════════════════════════════════════════════════════════════
write_all_configs() {
    phase_header "7" "8" "Configuration, Workspace & Skills"

    # ── Claude Code permissions ──────────────────────────────────
    info "Claude Code permissions..."
    cat > "$KOVO_DIR/.claude/settings.local.json" << 'EOF'
{
  "permissions": {
    "allow": [
      "Bash(/opt/kovo/venv/bin/pip *)", "Bash(/opt/kovo/venv/bin/playwright *)",
      "Bash(/opt/kovo/venv/bin/python *)", "Bash(apt *)", "Bash(cat *)",
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
    cat > "$KOVO_DIR/config/settings.yaml" << SETTINGS_EOF
kovo:
  workspace: $KOVO_DIR/workspace
  data_dir: $KOVO_DIR/data
  log_dir: $KOVO_DIR/logs

telegram:
  token: \${TELEGRAM_BOT_TOKEN}
  allowed_users:
    - \${OWNER_TELEGRAM_ID}

ollama:
  url: http://10.0.1.212:11434
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
  quick_interval: 30
  full_interval: 6
  morning_time: "08:00"
  use_ollama: false

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
    ok "settings.yaml"

    # ── .env.template → .env ─────────────────────────────────────
    info ".env..."
    cat > "$KOVO_DIR/config/.env.template" << 'ENV_EOF'
# KOVO Environment Variables
# Fill in via the dashboard setup wizard or manually here.

TELEGRAM_BOT_TOKEN=
OWNER_TELEGRAM_ID=
TELEGRAM_API_ID=
TELEGRAM_API_HASH=
CLAUDE_CODE_OAUTH_TOKEN=
GROQ_API_KEY=
GITHUB_TOKEN=
GOOGLE_CREDENTIALS_PATH=/opt/kovo/config/google-credentials.json
# ELEVENLABS_API_KEY=
ENV_EOF
    if [[ ! -f "$KOVO_DIR/config/.env" ]]; then
        cp "$KOVO_DIR/config/.env.template" "$KOVO_DIR/config/.env"
        ok ".env created (fill via dashboard)"
    else ok ".env exists (preserved)"; fi

    # ── Permissions ──────────────────────────────────────────────
    chmod 700 "$KOVO_DIR/config"
    chmod 600 "$KOVO_DIR/config/.env.template" "$KOVO_DIR/config/.env"
    chmod 600 "$KOVO_DIR/.claude/settings.local.json"
    [[ -f "$KOVO_DIR/data/kovo.db" ]] && chmod 600 "$KOVO_DIR/data/kovo.db"
    ok "File permissions secured"

    # ── Workspace files ──────────────────────────────────────────
    info "Workspace files..."

    [[ ! -f "$WORKSPACE/SOUL.md" ]] && cat > "$WORKSPACE/SOUL.md" << 'EOF'
# SOUL.md
## UNCONFIGURED
This agent has not been configured yet.
Send any message on Telegram to start the onboarding interview.
EOF

    [[ ! -f "$WORKSPACE/USER.md" ]] && cat > "$WORKSPACE/USER.md" << 'EOF'
# USER.md
## UNCONFIGURED
Not configured yet — will be set during onboarding.
EOF

    [[ ! -f "$WORKSPACE/IDENTITY.md" ]] && cat > "$WORKSPACE/IDENTITY.md" << 'EOF'
# IDENTITY.md
## Name
Kovo
## Creature Type
Blue alien
## Visual Description
A friendly blue alien with big expressive eyes, two small antennae, rosy cheeks, and a warm smile.
Primary color: #378ADD (Kovo Blue).
## Emoji
👾
## UNCONFIGURED
Personality not set yet — will be personalised during onboarding.
EOF

    [[ ! -f "$WORKSPACE/MEMORY.md" ]] && printf "# MEMORY.md — Long-Term Memory\n\n## Preferences\n\n## Decisions\n\n## Facts\n\n## Projects\n\n## Action Items\n\n" > "$WORKSPACE/MEMORY.md"

    cat > "$WORKSPACE/AGENTS.md" << 'EOF'
# Sub-Agent Registry
## Main Agent
- **Name**: Kovo
- **SOUL**: /opt/kovo/workspace/SOUL.md
- **Tools**: all
- **Status**: active
## Sub-Agents
*No sub-agents yet. Kovo will recommend one when it notices repeated specialized requests.*
EOF

    cat > "$WORKSPACE/HEARTBEAT.md" << 'EOF'
# HEARTBEAT.md
## Every 30 Minutes (Ollama)
- [ ] Check disk > 85%, RAM > 80%, CPU load > 4.0
## Every 6 Hours (Claude)
- [ ] Full health report, memory review, auto-purge tmp/audio
## Every Morning 8:00 AM (Claude)
- [ ] Good morning briefing, pending tasks, overnight summary
## Every Sunday 3:00 AM
- [ ] Scan old photos/documents, send review message
## Every Sunday 7:00 AM (Claude)
- [ ] Full security audit, compare baseline, escalate if suspicious
## Every 80 Days
- [ ] Remind to top up prepaid SIM
EOF
    ok "Workspace: SOUL, USER, IDENTITY, MEMORY, AGENTS, HEARTBEAT"

    # ── Skills (6 default) ───────────────────────────────────────
    info "Writing 6 default skills..."

    # Skill stubs for the 4 new ones (report-builder and security-audit written in full by the existing bootstrap logic)
    for skill_name in server-health google-workspace browser phone-call; do
        local skill_dir="$WORKSPACE/skills/$skill_name"
        mkdir -p "$skill_dir"
    done

    cat > "$WORKSPACE/skills/server-health/SKILL.md" << 'EOF'
---
name: server-health
description: Quick server health check — CPU, RAM, disk, services, connectivity.
tools: [shell]
trigger: health, status, server, check, system, cpu, ram, disk, uptime, load
---
# Server Health Skill
## Quick Checks
- CPU load: `cat /proc/loadavg`
- RAM: `free -h`
- Disk: `df -h /opt`
- Services: `systemctl is-active kovo redis`
- Connectivity: ping Telegram API, Ollama, Google
## Output
Send results via Telegram. If any metric is critical, escalate.
EOF

    cat > "$WORKSPACE/skills/google-workspace/SKILL.md" << 'EOF'
---
name: google-workspace
description: Google Docs, Drive, Gmail, Calendar, Sheets integration procedures.
tools: [shell, google_api]
trigger: google, docs, drive, gmail, email, calendar, sheets, spreadsheet, document
---
# Google Workspace Skill
## Authentication
Run `/auth_google` in Telegram to start OAuth2 flow.
Credentials stored at /opt/kovo/config/google-credentials.json.
## Capabilities
- Create/edit Google Docs
- Upload/download from Drive
- Send/read Gmail
- Read Calendar events
- Read/write Sheets
EOF

    cat > "$WORKSPACE/skills/browser/SKILL.md" << 'EOF'
---
name: browser
description: Web browsing, scraping, screenshots using Playwright headless Chromium.
tools: [shell, browser]
trigger: browse, website, screenshot, scrape, web, page, url, fetch, open site
---
# Browser Skill
## Usage
Use Playwright with headless Chromium for:
- Taking screenshots of web pages
- Scraping content from URLs
- Filling forms and automating web tasks
- Monitoring web pages for changes
## Notes
- Always use headless mode
- Respect robots.txt
- Save screenshots to /opt/kovo/data/screenshots/
EOF

    cat > "$WORKSPACE/skills/phone-call/SKILL.md" << 'EOF'
---
name: phone-call
description: Place Telegram voice calls using Pyrogram userbot with TTS audio.
tools: [shell, telegram_call, tts]
trigger: call, phone, voice call, ring, urgent call, emergency
---
# Phone Call Skill
## Setup
1. Get a second Telegram account (spare number/eSIM)
2. Set TELEGRAM_API_ID and TELEGRAM_API_HASH in .env
3. Run `/reauth_caller +PHONENUMBER` in Telegram
4. Enter OTP when prompted
## Usage
`/call Hey, the disk is almost full!`
Or send urgent messages — the agent decides when to call.
## Fallback
If call not answered in 30s, send voice message instead.
## TTS Voice
Configured in settings.yaml: en-US-AvaMultilingualNeural (free edge-tts).
EOF

    # report-builder and security-audit are large — only write if missing
    if [[ ! -f "$WORKSPACE/skills/report-builder/SKILL.md" ]]; then
        cat > "$WORKSPACE/skills/report-builder/SKILL.md" << 'EOF'
---
name: report-builder
description: Generate beautiful HTML reports — system health, status pages, weekly summaries.
tools: [shell]
trigger: report, dashboard, health report, status page, weekly report, generate report
---
# Report Builder
Generate single-file HTML reports with dark/light mode, animated charts, responsive layout.
Output: /opt/kovo/data/documents/Report_Name_YYYYMMDD.html
EOF
    fi

    if [[ ! -f "$WORKSPACE/skills/security-audit/SKILL.md" ]]; then
        cat > "$WORKSPACE/skills/security-audit/SKILL.md" << 'EOF'
---
name: security-audit
description: Deep security audit — network, packages, users, files, processes, malware.
tools: [shell]
trigger: security, audit, scan, vulnerability, ports, malware, rootkit, suspicious
---
# Security Audit Skill
Baseline at /opt/kovo/data/security_baseline.json.
Commands: /audit, /audit reset, /audit ports, /audit packages
Schedule: Every Sunday 7:00 AM.
EOF
    fi

    ok "Skills: report-builder, security-audit, server-health, google-workspace, browser, phone-call"

    # ── TOOLS.md ─────────────────────────────────────────────────
    info "TOOLS.md..."
    cat > "$WORKSPACE/TOOLS.md" << 'EOF'
---
tools:
- { name: shell, status: configured, description: "Execute shell commands" }
- { name: browser, status: configured, description: "Playwright headless Chromium" }
- { name: tts, status: configured, description: "Text-to-speech (edge-tts)" }
- { name: ollama, status: not_configured, description: "Local LLM for heartbeats", config_needed: "Set Ollama host in dashboard" }
- { name: claude_cli, status: not_configured, description: "Claude Code CLI", config_needed: "Run claude login" }
- { name: whisper, status: not_configured, description: "Voice transcription", config_needed: "Set GROQ_API_KEY" }
- { name: telegram_call, status: not_configured, description: "Voice calls", config_needed: "Set TELEGRAM_API_ID/HASH" }
- { name: google_api, status: not_configured, description: "Google Workspace", config_needed: "Run /auth_google" }
- { name: github, status: not_configured, description: "GitHub integration", config_needed: "Set GITHUB_TOKEN" }
---
# Tool Registry
Agents check this before using a tool and notify the owner if missing/unconfigured.
EOF
    ok "TOOLS.md (9 tools)"

    # ── Scripts ──────────────────────────────────────────────────
    info "Utility scripts..."

    cat > "$KOVO_DIR/scripts/backup.sh" << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/kovo/data/backups"
DATE=$(date +%Y%m%d)
mkdir -p "$BACKUP_DIR"
tar czf "$BACKUP_DIR/workspace_$DATE.tar.gz" -C /opt/kovo workspace/
[ -f /opt/kovo/data/security_baseline.json ] && cp /opt/kovo/data/security_baseline.json "$BACKUP_DIR/security_baseline_$DATE.json"
find "$BACKUP_DIR" -name "workspace_*.tar.gz" -mtime +30 -delete
find "$BACKUP_DIR" -name "security_baseline_*.json" -mtime +30 -delete
echo "✓ Backup: $BACKUP_DIR/workspace_$DATE.tar.gz"
EOF
    chmod +x "$KOVO_DIR/scripts/backup.sh"

    cat > "$KOVO_DIR/scripts/health-check.sh" << 'HCEOF'
#!/bin/bash
G='\033[38;5;114m' Y='\033[38;5;221m' R='\033[38;5;203m' B='\033[38;5;75m' N='\033[0m' D='\033[2m'
echo -e "\n${B}KOVO Health Check${N} ${D}$(date '+%Y-%m-%d %H:%M')${N}\n"
c() { if eval "$2" &>/dev/null; then echo -e "  ${G}✓${N} $1"; else echo -e "  ${R}✗${N} $1"; fi }
c "KOVO service" "systemctl is-active --quiet kovo"
c "Redis" "redis-cli ping | grep -q PONG"
c "Python venv" "[ -f /opt/kovo/venv/bin/python ]"
c "Claude CLI" "command -v claude"
RAM=$(free | awk '/^Mem:/{printf "%.0f",$3/$2*100}')
DISK=$(df /opt --output=pcent | tail -1 | tr -d ' %')
LOAD=$(cat /proc/loadavg | cut -d' ' -f2)
echo -e "\n  RAM: ${RAM}%  Disk: ${DISK}%  Load: ${LOAD}\n"
HCEOF
    chmod +x "$KOVO_DIR/scripts/health-check.sh"
    ok "scripts: backup.sh, health-check.sh"

    # ── Logrotate ────────────────────────────────────────────────
    if [[ ! -f /etc/logrotate.d/kovo ]]; then
        sudo tee /etc/logrotate.d/kovo > /dev/null << 'EOF'
/opt/kovo/logs/gateway.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
    copytruncate
}
EOF
        ok "Logrotate config"
    fi

    # ── CLAUDE.md ────────────────────────────────────────────────
    if [[ -f /tmp/CLAUDE.md ]]; then
        cp /tmp/CLAUDE.md "$KOVO_DIR/CLAUDE.md"
        ok "CLAUDE.md (from /tmp)"
    elif [[ -f "$KOVO_DIR/CLAUDE.md" ]]; then
        ok "CLAUDE.md exists"
    else
        warn "CLAUDE.md not found — place at $KOVO_DIR/CLAUDE.md"
    fi

    save_state 7
}

# ═══════════════════════════════════════════════════════════════════
#  PHASE 8 — Systemd, Verification, Dashboard Build & Launch
# ═══════════════════════════════════════════════════════════════════
finalize_and_launch() {
    phase_header "8" "8" "Service, Verification & Dashboard"

    # ── Systemd ──────────────────────────────────────────────────
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

    # ── Verification ─────────────────────────────────────────────
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "  ${BOLD}${WHITE}Verification${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    local passed=0 failed=0
    v() {
        if eval "$2" &>/dev/null; then ok "$1"; passed=$((passed+1))
        else fail "$1"; failed=$((failed+1)); fi
    }

    v "Python 3.13+"        "python3 --version | grep -qE '3\.1[3-9]'"
    v "Node.js 22+"         "node --version | grep -qE 'v2[2-9]'"
    v "npm"                 "npm --version"
    v "Claude Code CLI"     "command -v claude"
    v "Redis running"       "redis-cli ping 2>/dev/null | grep -q PONG"
    v "venv"                "[ -f $VENV/bin/python ]"
    v "FastAPI"             "$VENV/bin/python -c 'import fastapi'"
    v "Telegram lib"        "$VENV/bin/python -c 'import telegram'"
    v "PyTorch"             "$VENV/bin/python -c 'import torch'"
    v "Playwright"          "$VENV/bin/python -c 'import playwright'"
    v "Chromium"            "[ -d $HOME/.cache/ms-playwright ]"
    v "Pillow (mascot)"     "$VENV/bin/python -c 'import PIL'"
    v "ffmpeg"              "command -v ffmpeg"
    v "ClamAV"              "command -v clamscan"
    v "chkrootkit"          "command -v chkrootkit"
    v "rkhunter"            "command -v rkhunter"
    v "SOUL.md"             "[ -f $WORKSPACE/SOUL.md ]"
    v "settings.yaml"       "[ -f $KOVO_DIR/config/settings.yaml ]"
    v ".env"                "[ -f $KOVO_DIR/config/.env ]"
    v "permissions JSON"    "[ -f $KOVO_DIR/.claude/settings.local.json ]"
    v "systemd service"     "[ -f /etc/systemd/system/kovo.service ]"
    v "backup script"       "[ -x $KOVO_DIR/scripts/backup.sh ]"
    v "6 skills"            "[ $(find $WORKSPACE/skills -name SKILL.md | wc -l) -ge 6 ]"
    v "data directories"    "[ -d $KOVO_DIR/data/backups ]"

    local disk_gb=$(( $(df /opt --output=avail | tail -1 | tr -d ' ') / 1048576 ))
    if (( disk_gb >= 10 )); then ok "Disk: ${disk_gb}GB free"; passed=$((passed+1))
    else warn "Disk: ${disk_gb}GB free"; failed=$((failed+1)); fi

    echo ""
    local total=$((passed+failed))
    if (( failed == 0 )); then
        echo -e "  ${GREEN}${BOLD}$passed/$total checks passed${NC}"
    else
        echo -e "  ${YELLOW}${BOLD}$passed/$total passed${NC} ${DIM}($failed failed)${NC}"
    fi

    # ── Dashboard Build ──────────────────────────────────────────
    echo ""
    info "Building dashboard frontend..."
    local dash_dir="$KOVO_DIR/src/dashboard/frontend"
    if [ -d "$dash_dir" ] && [ -f "$dash_dir/package.json" ]; then
        cd "$dash_dir"
        npm install --silent 2>&1 | tail -1
        if npm run build 2>/dev/null; then
            ok "Dashboard built"
        else
            warn "Dashboard build failed — will work in dev mode"
        fi
        cd "$KOVO_DIR"
    else
        warn "Dashboard frontend not found — will be built by Claude Code"
    fi

    # ── Done! ────────────────────────────────────────────────────
    clear_state

    local vm_ip=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "your-ip")

    echo ""
    echo -e "${BLUE}${BOLD}"
    echo "   ╔══════════════════════════════════════════════════╗"
    echo "   ║                                                  ║"
    echo "   ║           KOVO is installed!                     ║"
    echo "   ║                                                  ║"
    echo "   ╚══════════════════════════════════════════════════╝"
    echo -e "${NC}"

    echo -e "  ${WHITE}What's next${NC}"
    echo ""
    echo -e "  KOVO needs ${WHITE}API keys and secrets${NC} before it can run."
    echo -e "  Configure everything through the dashboard:"
    echo ""
    echo -e "    ${CYAN}1${NC} Start the setup wizard:"
    echo ""
    echo -e "       ${CYAN}cd /opt/kovo && source venv/bin/activate${NC}"
    echo -e "       ${CYAN}python scripts/setup-wizard.py${NC}"
    echo ""
    echo -e "       Then open: ${WHITE}http://${vm_ip}:9090/setup${NC}"
    echo ""
    echo -e "    ${CYAN}2${NC} The wizard walks you through:"
    echo -e "       ${DIM}• Telegram bot token + your user ID${NC}"
    echo -e "       ${DIM}• Owner name + LLM preferences (Ollama)${NC}"
    echo -e "       ${DIM}• Optional: Groq, GitHub, Google${NC}"
    echo -e "       ${DIM}• Build KOVO with Claude Code${NC}"
    echo -e "       ${DIM}• Start the service${NC}"
    echo ""
    echo -e "  ${BLUE}──────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${WHITE}Quick commands${NC}  ${DIM}(after setup)${NC}"
    echo -e "  ${DIM}$KOVO_DIR/scripts/health-check.sh${NC}  ${GRAY}quick status${NC}"
    echo -e "  ${DIM}$KOVO_DIR/scripts/backup.sh${NC}        ${GRAY}backup workspace${NC}"
    echo -e "  ${DIM}sudo journalctl -fu kovo${NC}           ${GRAY}follow logs${NC}"
    echo -e "  ${DIM}sudo systemctl restart kovo${NC}        ${GRAY}restart agent${NC}"
    echo ""
    echo -e "  ${GRAY}Full log: ${LOG_FILE}${NC}"
    echo ""
}

# ═══════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════
main() {
    local start=0
    if $RESUME; then
        start=$(load_state)
        if (( start > 0 )); then
            show_banner
            info "Resuming from phase $((start+1))..."
            # Reload saved port config
            if [[ -f "$KOVO_DIR/config/settings.yaml" ]]; then
                GATEWAY_PORT=$(grep -A1 'gateway:' "$KOVO_DIR/config/settings.yaml" 2>/dev/null | grep 'port:' | awk '{print $2}' || echo "8080")
                DASHBOARD_PORT=$(grep -A1 'dashboard:' "$KOVO_DIR/config/settings.yaml" 2>/dev/null | grep 'port:' | awk '{print $2}' || echo "3000")
            fi
        else info "No previous state — starting fresh."; fi
    fi

    (( start < 1 )) && preflight
    (( start < 2 )) && authenticate_claude
    (( start < 3 )) && configure_network
    (( start < 4 )) && install_everything
    (( start < 5 )) && setup_node_and_structure
    (( start < 6 )) && install_python_env
    (( start < 7 )) && write_all_configs
    (( start < 8 )) && finalize_and_launch

    trap - EXIT
}

main
