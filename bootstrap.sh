#!/bin/bash
# ============================================================
# Kovo Bootstrap v4.0
# For: Ubuntu 25.10 (Questing), Python 3.13, Node 22+
# VM: 8GB RAM, 50GB+ disk
#
# Run: bash bootstrap.sh
# ============================================================

set +e

# --- Color helpers ---
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'
step() { echo -e "\n${GREEN}[STEP]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; }
ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
ERRORS=0

KOVO_DIR="/opt/kovo"
VENV="$KOVO_DIR/venv"
WORKSPACE="$KOVO_DIR/workspace"

echo -e "${GREEN}"
echo "  ╔══════════════════════════════════════╗"
echo "  ║        👾  Kovo Bootstrap v4.0       ║"
echo "  ║    Ubuntu 25.10 · Python 3.13        ║"
echo "  ╚══════════════════════════════════════╝"
echo -e "${NC}"

# ============================================================
# Step 1/12: System update
# ============================================================
step "1/16 — System update"
sudo apt update -y && sudo apt upgrade -y
ok "System packages updated"

# ============================================================
# Step 2/12: Core dependencies
# ============================================================
step "2/16 — Core dependencies"
sudo apt install -y \
    python3 python3.13-venv python3-pip \
    git curl wget jq \
    build-essential ffmpeg sqlite3 \
    htop tmux ca-certificates gnupg
ok "Core dependencies installed"

# ============================================================
# Step 3/12: Redis
# ============================================================
step "3/16 — Redis"
sudo apt install -y redis-tools redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server
ok "Redis installed and running"

# ============================================================
# Step 4/16: Security audit tools
# ============================================================
step "4/16 — Security audit tools"
sudo apt install -y clamav clamav-daemon chkrootkit rkhunter
# Update ClamAV virus definitions (non-fatal if offline)
sudo systemctl stop clamav-freshclam 2>/dev/null || true
sudo freshclam 2>/dev/null || warn "ClamAV definitions update failed (run 'sudo freshclam' later)"
sudo systemctl start clamav-freshclam 2>/dev/null || true
ok "Security tools installed (ClamAV, chkrootkit, rkhunter)"

# ============================================================
# Step 5/16: Node.js 22 via NodeSource
# ============================================================
step "5/16 — Node.js 22"
if command -v node &>/dev/null; then
    NODE_VER=$(node --version)
    ok "Node already installed: $NODE_VER (skipping NodeSource)"
else
    curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
    sudo apt install -y nodejs
    ok "Node.js $(node --version) installed"
fi
# Verify npm came with it — do NOT install ubuntu's npm package separately
if ! command -v npm &>/dev/null; then
    fail "npm not found — something went wrong with NodeSource install"
    ERRORS=$((ERRORS + 1))
else
    ok "npm $(npm --version) available"
fi

# ============================================================
# Step 6/16: Claude Code CLI
# ============================================================
step "6/16 — Claude Code CLI"
if command -v claude &>/dev/null; then
    ok "Claude Code already installed ($(claude --version 2>/dev/null || echo 'unknown version'))"
else
    sudo npm install -g @anthropic-ai/claude-code
    ok "Claude Code CLI installed"
fi

# ============================================================
# Step 7/16: Project structure
# ============================================================
step "7/16 — Project structure"
sudo mkdir -p "$KOVO_DIR"
sudo chown "$USER:$USER" "$KOVO_DIR"

# Source directories
mkdir -p "$KOVO_DIR"/{src,config,scripts,scripts/experiments,tests,logs,systemd}

# Data subdirectories (storage manager expects these)
mkdir -p "$KOVO_DIR"/data/{tmp,audio,photos,documents,images,screenshots,backups}
touch "$KOVO_DIR/data/kovo.db"

# Workspace
mkdir -p "$WORKSPACE"/{memory/archive,skills,checklists,docs,agents}
mkdir -p "$WORKSPACE/skills/report-builder/templates"
mkdir -p "$WORKSPACE/skills/security-audit"

# Claude Code config directory
mkdir -p "$KOVO_DIR/.claude"

ok "Directory structure created"

# ============================================================
# Step 8/16: Clone Kovo source from GitHub
# ============================================================
step "8/16 — Clone Kovo source"
KOVO_REPO="https://github.com/Ava-AgentOne/kovo.git"

if [ -d "$KOVO_DIR/src" ] && [ -f "$KOVO_DIR/src/gateway/main.py" ]; then
    warn "Source code already exists — pulling latest"
    git -C "$KOVO_DIR" pull origin main 2>/dev/null || warn "Git pull failed — using existing code"
    ok "Source code up to date"
else
    git clone "$KOVO_REPO" "$KOVO_DIR/repo-tmp"
    cp -r "$KOVO_DIR/repo-tmp/src"             "$KOVO_DIR/src"
    [ -f "$KOVO_DIR/repo-tmp/requirements.txt" ] && \
        cp "$KOVO_DIR/repo-tmp/requirements.txt" "$KOVO_DIR/requirements.txt"
    [ -f "$KOVO_DIR/repo-tmp/CLAUDE.md" ] && \
        cp "$KOVO_DIR/repo-tmp/CLAUDE.md"        "$KOVO_DIR/CLAUDE.md"
    [ -f "$KOVO_DIR/repo-tmp/DOCS.md" ] && \
        cp "$KOVO_DIR/repo-tmp/DOCS.md"          "$KOVO_DIR/DOCS.md"
    rm -rf "$KOVO_DIR/repo-tmp"
    ok "Source code cloned from GitHub"
fi

# ============================================================
# Step 9/16: Sudo NOPASSWD
# ============================================================
step "9/16 — Sudo NOPASSWD"
echo "$USER ALL=(ALL) NOPASSWD: ALL" | sudo tee /etc/sudoers.d/kovo > /dev/null
sudo chmod 440 /etc/sudoers.d/kovo
ok "Sudo NOPASSWD configured for $USER"

# ============================================================
# Step 10/16: Claude Code permissions
# ============================================================
step "10/16 — Claude Code permissions (prevents prompts during build)"
cat > "$KOVO_DIR/.claude/settings.local.json" << 'EOF'
{
  "permissions": {
    "allow": [
      "Bash(/opt/kovo/venv/bin/pip *)",
      "Bash(/opt/kovo/venv/bin/playwright *)",
      "Bash(/opt/kovo/venv/bin/python *)",
      "Bash(apt *)",
      "Bash(cat *)",
      "Bash(cd *)",
      "Bash(chmod *)",
      "Bash(chown *)",
      "Bash(cp *)",
      "Bash(curl *)",
      "Bash(cut *)",
      "Bash(date *)",
      "Bash(df *)",
      "Bash(diff *)",
      "Bash(dirname *)",
      "Bash(docker *)",
      "Bash(du *)",
      "Bash(echo *)",
      "Bash(env *)",
      "Bash(ffmpeg *)",
      "Bash(find *)",
      "Bash(free *)",
      "Bash(gh *)",
      "Bash(grep *)",
      "Bash(head *)",
      "Bash(hostname *)",
      "Bash(id *)",
      "Bash(journalctl *)",
      "Bash(kill *)",
      "Bash(ln *)",
      "Bash(ls *)",
      "Bash(lsof *)",
      "Bash(mkdir *)",
      "Bash(mv *)",
      "Bash(node *)",
      "Bash(npm *)",
      "Bash(npx *)",
      "Bash(ps *)",
      "Bash(pwd)",
      "Bash(readlink *)",
      "Bash(redis-cli *)",
      "Bash(rm *)",
      "Bash(sed *)",
      "Bash(sort *)",
      "Bash(source *)",
      "Bash(sudo *)",
      "Bash(systemctl *)",
      "Bash(tail *)",
      "Bash(tar *)",
      "Bash(tee *)",
      "Bash(test *)",
      "Bash(touch *)",
      "Bash(tr *)",
      "Bash(uname *)",
      "Bash(uniq *)",
      "Bash(wc *)",
      "Bash(wget *)",
      "Bash(which *)",
      "Bash(whoami)",
      "Bash(xargs *)",
      "Edit(*)"
    ]
  }
}
EOF
ok "Claude Code permissions file written (61 entries)"

# ============================================================
# Step 11/16: Python venv + dependencies
# ============================================================
step "11/16 — Python venv + dependencies"
python3 -m venv "$VENV"
source "$VENV/bin/activate"
pip install --upgrade pip

# PyTorch CPU-only FIRST — never pull CUDA/GPU packages on this VM
echo "  Installing PyTorch (CPU-only)..."
pip install torch --index-url https://download.pytorch.org/whl/cpu

# Whisper without deps first — avoids pulling GPU triton
echo "  Installing Whisper (--no-deps)..."
pip install openai-whisper --no-deps

# Whisper transitive deps (manually, non-GPU)
pip install tiktoken more-itertools numba tqdm numpy regex

# Everything else
echo "  Installing remaining packages..."
pip install \
    fastapi \
    "uvicorn[standard]" \
    "python-telegram-bot[webhooks]" \
    httpx \
    pydantic \
    python-dotenv \
    PyYAML \
    apscheduler \
    psutil \
    playwright \
    pyrogram \
    tgcrypto \
    py-tgcalls \
    edge-tts \
    google-api-python-client \
    google-auth-httplib2 \
    google-auth-oauthlib \
    PyGithub \
    pytest \
    pytest-asyncio

ok "Python venv and all dependencies installed"

# ============================================================
# Step 12/16: Python dependencies from requirements.txt
# ============================================================
step "12/16 — Python dependencies"
if [ -f "$KOVO_DIR/requirements.txt" ]; then
    "$VENV/bin/pip" install -r "$KOVO_DIR/requirements.txt" --quiet
    ok "Python dependencies installed from requirements.txt"
else
    warn "requirements.txt not found — skipping (run after git clone)"
fi

# ============================================================
# Step 13/16: Playwright browser
# ============================================================
step "13/16 — Playwright Chromium"
"$VENV/bin/playwright" install chromium
"$VENV/bin/playwright" install-deps chromium
ok "Playwright Chromium installed"

# ============================================================
# Step 14/16: Dashboard frontend
# ============================================================
step "14/16 — Dashboard frontend"
DASHBOARD_DIR="$KOVO_DIR/src/dashboard/frontend"
if [ -d "$DASHBOARD_DIR" ] && [ -f "$DASHBOARD_DIR/package.json" ]; then
    cd "$DASHBOARD_DIR"
    npm install --silent
    npm run build 2>/dev/null && ok "Dashboard built successfully" || \
        warn "Dashboard build failed — will run in dev mode"
    cd "$KOVO_DIR"
else
    warn "Dashboard frontend not found — skipping (run after git clone)"
fi

# ============================================================
# Step 15/16: Workspace files and config
# ============================================================
step "15/16 — Workspace files and config"

# --- SOUL.md (UNCONFIGURED — onboarding fills this in) ---
if [ ! -f "$WORKSPACE/SOUL.md" ]; then
cat > "$WORKSPACE/SOUL.md" << 'EOF'
# SOUL.md

## UNCONFIGURED

This agent has not been configured yet.
Send any message on Telegram to start the onboarding interview.
EOF
ok "SOUL.md created (unconfigured — onboarding will fill this in)"
else
    ok "SOUL.md already exists (skipping)"
fi

# --- USER.md (placeholder — onboarding fills this in) ---
if [ ! -f "$WORKSPACE/USER.md" ]; then
cat > "$WORKSPACE/USER.md" << 'EOF'
# USER.md

## UNCONFIGURED

Not configured yet — will be set during onboarding interview.
EOF
ok "USER.md created (placeholder)"
else
    ok "USER.md already exists (skipping)"
fi

# --- IDENTITY.md (placeholder — onboarding fills this in) ---
if [ ! -f "$WORKSPACE/IDENTITY.md" ]; then
cat > "$WORKSPACE/IDENTITY.md" << 'EOF'
# IDENTITY.md

## Name
Kovo

## Creature Type
Blue alien

## Visual Description
A friendly blue alien with big expressive eyes, two small antennae with glowing tips, rosy cheeks, and a warm smile. Round body, stubby arms and legs. Primary color: #378ADD (Kovo Blue).

## Vibe
Playful, curious, and helpful. Always watching out for you. Small but capable — handles everything from health checks to security audits.

## Emoji
👾

## UNCONFIGURED
Personality and owner details not set yet — will be personalised during onboarding.
EOF
ok "IDENTITY.md created (placeholder)"
else
    ok "IDENTITY.md already exists (skipping)"
fi

# --- MEMORY.md (categorized format) ---
if [ ! -f "$WORKSPACE/MEMORY.md" ]; then
cat > "$WORKSPACE/MEMORY.md" << 'EOF'
# MEMORY.md — Long-Term Memory

## Preferences

## Decisions

## Facts

## Projects

## Action Items

EOF
ok "MEMORY.md created (categorized format)"
else
    ok "MEMORY.md already exists (skipping)"
fi

# --- AGENTS.md ---
cat > "$WORKSPACE/AGENTS.md" << 'EOF'
# Sub-Agent Registry

This file lists all active sub-agents created by Kovo.
The main agent (Kovo) handles everything by default.
Sub-agents are created on demand when Esam approves a recommendation.

## Main Agent
- **Name**: Kovo
- **SOUL**: /opt/kovo/workspace/SOUL.md
- **Tools**: all (shell, browser, google_api, telegram_call, tts, ollama, claude_cli, whisper)
- **Status**: active

## Sub-Agents

<!-- Sub-agents are added here automatically when created.
Format:
### {name}
- **SOUL**: workspace/agents/{name}/SOUL.md
- **Tools**: [list of tool names]
- **Memory**: workspace/agents/{name}/memory/
- **Created**: YYYY-MM-DD
- **Purpose**: one-line description
-->

*No sub-agents yet. Kovo will recommend one when it notices repeated specialised requests.*

## Sub-Agent Creation Flow
1. Kovo notices Esam repeatedly asks for a specific type of job
2. Kovo recommends creating a sub-agent via Telegram message
3. Esam replies "yes" or "/create_agent {name}"
4. Kovo creates workspace/agents/{name}/ with SOUL.md, tools.yaml, memory/
5. Kovo registers it in this file
6. Sub-agent is live — Kovo delegates to it and summarises results
EOF
ok "AGENTS.md written"

# --- HEARTBEAT.md ---
cat > "$WORKSPACE/HEARTBEAT.md" << 'EOF'
# HEARTBEAT.md

## Every 30 Minutes (Ollama)
- [ ] Check disk usage — alert if any mount > 85%
- [ ] Check RAM usage — alert if > 80%
- [ ] Check CPU load — alert if 5min avg > 4.0

## Every 6 Hours (Claude)
- [ ] Full system health report
- [ ] Review and summarize daily memory
- [ ] Check caller session health
- [ ] Auto-purge old tmp/audio/screenshots (tier-1, no approval needed)
- [ ] Alert if disk free < 15%

## Every Morning at 8:00 AM (Claude)
- [ ] Good morning briefing
- [ ] Pending tasks from yesterday
- [ ] System overnight health summary

## Every Sunday at 3:00 AM
- [ ] Scan for old photos/documents/images (tier-2)
- [ ] Send Telegram review message if purgeable files found

## Every Sunday at 7:00 AM (Claude)
- [ ] Full security audit (network, packages, users, files, processes)
- [ ] Compare against baseline — report changes
- [ ] Escalate via Telegram call if suspicious activity detected

## Every 80 Days
- [ ] Remind Esam to top up prepaid SIM for caller account
EOF
ok "HEARTBEAT.md written"

# --- report-builder SKILL.md ---
cat > "$WORKSPACE/skills/report-builder/SKILL.md" << 'EOF'
---
name: report-builder
description: Generate beautiful, modern HTML reports for any purpose — system health, project status, analytics, weekly summaries, incident reports, or any structured data. Produces a self-contained single-file HTML with dark/light mode toggle, animated charts, responsive cards, and email-ready output.
tools: [shell]
trigger: report, dashboard, health report, status page, weekly report, generate report, build report, system report, morning briefing report, email report
---

# Report Builder

## Purpose

Generate stunning, single-file HTML reports from any structured data. The output is self-contained (inline CSS/JS, no external dependencies except Google Fonts) and can be:

- Served on the Kovo dashboard at port 8080
- Attached to emails via Gmail
- Sent as a file via Telegram
- Opened directly in any browser
- Printed to PDF from the browser

## When to Use

Trigger this skill when asked to:
- Create/generate/build any kind of report
- Make a dashboard or status page
- Visualize metrics, KPIs, or structured data
- Produce a summary report (weekly, monthly, project, incident, etc.)
- Generate something to send via email as an HTML attachment
- Generate a morning briefing as a visual report

Report types: system health, morning briefings, storage reports, project status, weekly digests, incident reports, analytics dashboards.

## Architecture

Single self-contained HTML file with:
- Inline CSS using custom properties for theming
- Inline SVG icons (no icon libraries)
- Vanilla JS for theme toggle only
- CSS animations (no JS animation libraries)
- Google Fonts link (Outfit + JetBrains Mono) — gracefully degrades to system fonts if offline

## Report Skeleton

Every report follows this structure — pick the components you need:

Header (always) → Hero with Score Ring + Stat Cards (optional) → Sections with any mix of: Info Grid, Metric Cards, Data Tables, List Rows, Item Cards, Score Breakdown Cards, Timeline, Tag Cards, Recommendations → Footer (always)

## Available Components (13 total)

1. **Header** — title, subtitle, status badge (green/warning/critical/info)
2. **Score Ring** — circular gauge, animated fill. Offset = 439.82 - (439.82 × pct / 100)
3. **Stat Cards** — KPI cards with colored left accent (cyan/green/purple/orange)
4. **Info Grid** — key-value pairs, 2-4 column grid
5. **Metric Cards with Progress** — percentage bar + detail rows
6. **Data Table** — header row + data rows with status pills
7. **List Rows** — grid items with status badges
8. **Item Cards** — dot + label + badge (for software, tools, tags)
9. **Score Breakdown** — accent bar, score badge, progress, sparkline
10. **Timeline** — vertical dots with dashed connectors
11. **Tag Cards** — small centered cards with top accent
12. **Numbered Recommendations** — ordered items with colored number badges
13. **Section Divider** — labeled horizontal line

## Color System

| Token | Use For |
|-------|---------|
| cyan | Primary metrics, default accent |
| green | Success, healthy, complete |
| yellow | Warning, needs attention |
| red | Error, critical, failed |
| purple | Secondary, informational |
| orange | Tertiary, in-progress |

Percentage metrics (lower=better): 0-30% green, 31-60% cyan, 61-80% yellow, 81-100% red
Score metrics (higher=better): 90-100 green, 70-89 cyan, 50-69 yellow, 0-49 red

## Report Type -> Components

| Type | Use |
|------|-----|
| System Health | Score Ring + Stat Cards + Metric Cards + Score Breakdown + Recommendations |
| Morning Briefing | Stat Cards + List Rows + Timeline + Recommendations |
| Storage Report | Metric Cards + Score Breakdown + Recommendations |
| Weekly Digest | Stat Cards + List Rows + Timeline + Tag Cards + Recommendations |
| Incident Report | Info Grid + Timeline + List Rows + Recommendations |

## How to Build a Report

1. Read templates/report-template.html as your base
2. Set header: title, subtitle, status badge
3. Choose components based on the report type
4. Remove unused sections
5. Inject live data from shell commands (df, free, systemctl, etc.)
6. Calculate derived values: score ring offsets, color assignments
7. Set footer date
8. Save to /opt/kovo/data/documents/Report_Name_YYYYMMDD.html

## Template Location

/opt/kovo/workspace/skills/report-builder/templates/report-template.html
EOF
ok "report-builder/SKILL.md written"

# --- security-audit SKILL.md ---
cat > "$WORKSPACE/skills/security-audit/SKILL.md" << 'EOF'
---
name: security-audit
description: Deep security audit of the VM — network, packages, users, files, processes, malware. Tracks baselines and reports only changes. Escalates suspicious activity via Telegram call.
tools: [shell]
trigger: security, audit, scan, vulnerability, ports, malware, rootkit, packages, suspicious, intrusion, hardening, security check, security report
---

# Security Audit Skill

## Purpose

Perform a comprehensive security audit of the Kovo VM. Maintains a baseline of system state and alerts on unauthorized changes. Escalates suspicious findings via Telegram voice call.

## Audit Categories

### 1. Network — open ports (ss -tlnp), outbound connections, firewall status
### 2. Packages — installed vs baseline, flag unauthorized new packages, pending security updates
### 3. Users & Access — new accounts, sudo grants, SSH config, failed logins
### 4. File System — new SUID binaries, world-writable files, cron job changes, config permissions
### 5. Processes — unknown processes, high resource usage, root processes
### 6. Malware — ClamAV scan, rootkit check (chkrootkit/rkhunter), suspicious files in /tmp /dev/shm

## Baseline

Stored at: /opt/kovo/data/security_baseline.json
- First run creates baseline (no alerts)
- Subsequent runs compare and report changes only
- Reset with: /audit reset

## Escalation

- CALL: new user, new sudo, new SUID, malware, SSH root enabled, unauthorized package, suspicious files, 20+ failed logins
- TEXT WARNING: security updates pending, world-writable files, config permissions, unknown outbound connections
- TEXT CLEAN: no issues found

## Commands

- /audit — run full audit now
- /audit reset — reset baseline
- /audit baseline — show baseline summary
- /audit ports — quick port scan
- /audit packages — quick package diff

## Schedule

Every Sunday at 7:00 AM via heartbeat scheduler.
EOF
ok "security-audit/SKILL.md written"

# --- report-builder template HTML ---
cat > "$WORKSPACE/skills/report-builder/templates/report-template.html" << 'HTMLEOF'
<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Kovo — System Health Report</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
    :root{--bg:#0d1117;--bg2:#161b24;--bg3:#1c2333;--border:rgba(255,255,255,0.07);--border-hover:rgba(255,255,255,0.14);--text:#e6edf3;--text-dim:#8b949e;--text-muted:#484f58;--shadow:0 4px 24px rgba(0,0,0,0.45);--shadow-sm:0 2px 10px rgba(0,0,0,0.3);--cyan:#22d3ee;--cyan-dim:rgba(34,211,238,0.12);--green:#4ade80;--green-dim:rgba(74,222,128,0.12);--yellow:#fbbf24;--yellow-dim:rgba(251,191,36,0.12);--red:#f87171;--red-dim:rgba(248,113,113,0.12);--purple:#a78bfa;--purple-dim:rgba(167,139,250,0.12);--orange:#fb923c;--orange-dim:rgba(251,146,60,0.12)}
    [data-theme="light"]{--bg:#f6f8fc;--bg2:#ffffff;--bg3:#eef2f8;--border:rgba(0,0,0,0.08);--border-hover:rgba(0,0,0,0.16);--text:#1c2333;--text-dim:#57606a;--text-muted:#a0aabb;--shadow:0 4px 24px rgba(0,0,0,0.08);--shadow-sm:0 2px 10px rgba(0,0,0,0.05);--cyan:#0284c7;--cyan-dim:rgba(2,132,199,0.10);--green:#16a34a;--green-dim:rgba(22,163,74,0.10);--yellow:#b45309;--yellow-dim:rgba(180,83,9,0.10);--red:#dc2626;--red-dim:rgba(220,38,38,0.10);--purple:#7c3aed;--purple-dim:rgba(124,58,237,0.10);--orange:#c2410c;--orange-dim:rgba(194,65,12,0.10)}
    body{font-family:'Outfit',system-ui,sans-serif;background:var(--bg);color:var(--text);line-height:1.6;min-height:100vh;position:relative;overflow-x:hidden;transition:background 0.25s,color 0.25s}
    body::before{content:'';position:fixed;inset:0;background:radial-gradient(ellipse 80% 50% at 5% 0%,rgba(34,211,238,0.04) 0%,transparent 60%),radial-gradient(ellipse 60% 40% at 95% 100%,rgba(167,139,250,0.04) 0%,transparent 60%);pointer-events:none;z-index:0}
    .top-bar{position:fixed;top:0;left:0;right:0;height:3px;background:linear-gradient(90deg,var(--cyan),var(--purple),var(--orange),var(--cyan));background-size:300% 100%;animation:shimmer 4s linear infinite;z-index:100}
    @keyframes shimmer{0%{background-position:0% 50%}100%{background-position:300% 50%}}
    .container{max-width:1100px;margin:0 auto;padding:56px 24px 80px;position:relative;z-index:1}
    .theme-toggle{position:fixed;top:18px;right:18px;z-index:200;background:var(--bg2);border:1px solid var(--border);color:var(--text-dim);border-radius:50%;width:40px;height:40px;display:flex;align-items:center;justify-content:center;cursor:pointer;font-size:17px;box-shadow:var(--shadow-sm);transition:border-color 0.2s,box-shadow 0.2s}
    .theme-toggle:hover{border-color:var(--border-hover);box-shadow:var(--shadow)}
    @keyframes fadeInUp{from{opacity:0;transform:translateY(18px)}to{opacity:1;transform:translateY(0)}}
    @keyframes ringFill{from{stroke-dashoffset:439.82}}
    @keyframes barGrow{from{width:0}}
    .anim{animation:fadeInUp 0.5s ease both}
    .anim-1{animation-delay:0.05s}.anim-2{animation-delay:0.12s}.anim-3{animation-delay:0.20s}
    .anim-4{animation-delay:0.28s}.anim-5{animation-delay:0.36s}.anim-6{animation-delay:0.44s}.anim-7{animation-delay:0.52s}
    .section{margin-bottom:40px}
    .section-title{font-size:11px;font-weight:600;letter-spacing:0.12em;text-transform:uppercase;color:var(--text-muted);margin-bottom:14px}

    /* Header */
    .report-header{margin-bottom:48px}
    .report-header-meta{display:flex;align-items:center;gap:12px;margin-bottom:10px}
    .report-eyebrow{font-size:12px;font-weight:500;color:var(--text-muted);letter-spacing:0.08em;text-transform:uppercase;font-family:'JetBrains Mono',monospace}
    .report-title{font-size:36px;font-weight:700;color:var(--text);line-height:1.2;margin-bottom:6px}
    .report-subtitle{font-size:15px;color:var(--text-dim)}
    .status-badge{display:inline-flex;align-items:center;gap:6px;padding:4px 12px;border-radius:99px;font-size:12px;font-weight:600;letter-spacing:0.04em;text-transform:uppercase}
    .status-badge::before{content:'';width:6px;height:6px;border-radius:50%;background:currentColor}
    .badge-green{background:var(--green-dim);color:var(--green)}.badge-yellow{background:var(--yellow-dim);color:var(--yellow)}
    .badge-red{background:var(--red-dim);color:var(--red)}.badge-cyan{background:var(--cyan-dim);color:var(--cyan)}
    .badge-purple{background:var(--purple-dim);color:var(--purple)}.badge-orange{background:var(--orange-dim);color:var(--orange)}

    /* Hero */
    .hero{display:grid;grid-template-columns:220px 1fr;gap:24px;margin-bottom:40px}

    /* Score Ring */
    .score-ring-card{background:var(--bg2);border:1px solid var(--border);border-radius:16px;padding:28px 20px;display:flex;flex-direction:column;align-items:center;gap:14px;box-shadow:var(--shadow)}
    .score-ring-label{font-size:12px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:var(--text-dim)}
    .score-ring-wrapper{position:relative;display:inline-block;width:140px;height:140px}
    .score-ring-svg{width:140px;height:140px;transform:rotate(-90deg)}
    .score-ring-track{fill:none;stroke:var(--bg3);stroke-width:12}
    .score-ring-fill{fill:none;stroke-width:12;stroke-linecap:round;stroke-dasharray:439.82;animation:ringFill 1.3s cubic-bezier(0.4,0,0.2,1) both 0.3s}
    .score-ring-value{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center}
    .score-ring-number{font-size:34px;font-weight:700;font-family:'JetBrains Mono',monospace;color:var(--text);line-height:1}
    .score-ring-unit{font-size:12px;color:var(--text-dim)}
    .score-ring-desc{font-size:13px;color:var(--text-dim);text-align:center;line-height:1.5}

    /* Stat Cards */
    .stat-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}
    .stat-card{background:var(--bg2);border:1px solid var(--border);border-left:3px solid var(--accent,var(--cyan));border-radius:12px;padding:16px 18px;box-shadow:var(--shadow-sm);position:relative;overflow:hidden}
    [data-theme="dark"] .stat-card::after{content:'';position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--accent,var(--cyan));filter:blur(8px);opacity:0.45}
    .stat-card-value{font-size:24px;font-weight:700;font-family:'JetBrains Mono',monospace;color:var(--text);line-height:1.2}
    .stat-card-label{font-size:12px;color:var(--text-dim);margin-top:3px}
    .stat-card-sub{font-size:11px;font-family:'JetBrains Mono',monospace;color:var(--text-muted);margin-top:6px}

    /* Info Grid */
    .info-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(195px,1fr));gap:10px}
    .info-item{background:var(--bg2);border:1px solid var(--border);border-radius:10px;padding:12px 16px}
    .info-item-key{font-size:10px;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.07em;margin-bottom:4px}
    .info-item-value{font-size:13px;font-family:'JetBrains Mono',monospace;color:var(--text);font-weight:500}

    /* Metric Cards */
    .metric-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px}
    .metric-card{background:var(--bg2);border:1px solid var(--border);border-radius:14px;padding:20px;box-shadow:var(--shadow-sm)}
    .metric-header{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:12px}
    .metric-name{font-size:13px;font-weight:600;color:var(--text-dim)}
    .metric-pct{font-size:24px;font-weight:700;font-family:'JetBrains Mono',monospace}
    .progress-track{height:6px;background:var(--bg3);border-radius:99px;overflow:hidden;margin-bottom:14px}
    .progress-fill{height:100%;border-radius:99px;animation:barGrow 1s cubic-bezier(0.4,0,0.2,1) both 0.4s}
    .metric-details{display:grid;grid-template-columns:1fr 1fr;gap:8px 12px}
    .metric-detail-row{display:flex;flex-direction:column;gap:2px}
    .metric-detail-label{font-size:10px;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.05em}
    .metric-detail-val{font-size:13px;font-family:'JetBrains Mono',monospace;color:var(--text)}

    /* Data Table */
    .data-table-wrap{background:var(--bg2);border:1px solid var(--border);border-radius:14px;overflow:hidden;box-shadow:var(--shadow-sm)}
    .data-table{width:100%;border-collapse:collapse}
    .data-table th{padding:11px 18px;text-align:left;font-size:11px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:var(--text-muted);background:var(--bg3);border-bottom:1px solid var(--border)}
    .data-table td{padding:12px 18px;font-size:13px;color:var(--text);border-bottom:1px solid var(--border)}
    .data-table tr:last-child td{border-bottom:none}
    .data-table tbody tr:hover td{background:var(--bg3);transition:background 0.15s}
    .data-table .mono{font-family:'JetBrains Mono',monospace;font-size:12px}
    .pill{display:inline-block;padding:2px 10px;border-radius:99px;font-size:11px;font-weight:600}
    .pill-green{background:var(--green-dim);color:var(--green)}.pill-yellow{background:var(--yellow-dim);color:var(--yellow)}
    .pill-red{background:var(--red-dim);color:var(--red)}.pill-cyan{background:var(--cyan-dim);color:var(--cyan)}
    .pill-purple{background:var(--purple-dim);color:var(--purple)}.pill-orange{background:var(--orange-dim);color:var(--orange)}

    /* List Rows */
    .list-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(255px,1fr));gap:10px}
    .list-row{background:var(--bg2);border:1px solid var(--border);border-radius:10px;padding:12px 16px;display:flex;align-items:center;justify-content:space-between;gap:12px}
    .list-row-label{font-size:13px;color:var(--text);font-weight:500}
    .list-row-sub{font-size:11px;font-family:'JetBrains Mono',monospace;color:var(--text-muted);margin-top:2px}

    /* Item Cards */
    .item-card-grid{display:flex;flex-wrap:wrap;gap:8px}
    .item-card{background:var(--bg2);border:1px solid var(--border);border-radius:8px;padding:7px 14px;display:flex;align-items:center;gap:8px;font-size:13px}
    .item-dot{width:6px;height:6px;border-radius:50%;flex-shrink:0}
    .item-label{color:var(--text);font-weight:500}
    .item-badge{font-size:11px;font-family:'JetBrains Mono',monospace;color:var(--text-muted)}

    /* Score Breakdown */
    .breakdown-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px}
    .breakdown-card{background:var(--bg2);border:1px solid var(--border);border-radius:14px;overflow:hidden;box-shadow:var(--shadow-sm)}
    .breakdown-accent{height:3px;background:linear-gradient(90deg,var(--bd-color,var(--cyan)),transparent)}
    .breakdown-body{padding:16px 18px}
    .breakdown-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}
    .breakdown-name{font-size:13px;font-weight:600;color:var(--text)}
    .breakdown-score{font-size:20px;font-weight:700;font-family:'JetBrains Mono',monospace}
    .breakdown-progress{height:4px;background:var(--bg3);border-radius:99px;overflow:hidden;margin-bottom:10px}
    .breakdown-progress-fill{height:100%;border-radius:99px;background:linear-gradient(90deg,var(--bd-color,var(--cyan)),transparent 110%);animation:barGrow 1s cubic-bezier(0.4,0,0.2,1) both 0.5s}
    .breakdown-desc{font-size:12px;color:var(--text-dim);margin-bottom:12px;line-height:1.5}
    .sparkline-wrap{background:var(--bg3);border-radius:8px;padding:8px 6px;height:56px}
    .sparkline{width:100%;height:100%}

    /* Timeline */
    .timeline{display:flex;flex-direction:column}
    .timeline-item{display:flex;gap:16px;position:relative}
    .timeline-left{display:flex;flex-direction:column;align-items:center;flex-shrink:0;width:28px}
    .timeline-dot{width:12px;height:12px;border-radius:50%;border:2px solid var(--tl-color,var(--cyan));background:var(--bg2);margin-top:5px;flex-shrink:0}
    .timeline-line{flex:1;width:1px;border-left:1px dashed var(--border);margin:4px 0}
    .timeline-item:last-child .timeline-line{display:none}
    .timeline-content{padding-bottom:20px;flex:1}
    .timeline-time{font-size:11px;font-family:'JetBrains Mono',monospace;color:var(--text-muted);margin-bottom:3px}
    .timeline-title{font-size:14px;font-weight:600;color:var(--text);margin-bottom:3px}
    .timeline-body{font-size:13px;color:var(--text-dim);line-height:1.5}

    /* Tag Cards */
    .tag-grid{display:flex;flex-wrap:wrap;gap:10px}
    .tag-card{background:var(--bg2);border:1px solid var(--border);border-top:3px solid var(--tag-color,var(--cyan));border-radius:10px;padding:12px 18px;text-align:center;min-width:90px}
    .tag-card-value{font-size:20px;font-weight:700;font-family:'JetBrains Mono',monospace;color:var(--tag-color,var(--cyan));display:block}
    .tag-card-label{font-size:11px;color:var(--text-dim);margin-top:2px}

    /* Recommendations */
    .rec-list{display:flex;flex-direction:column;gap:12px}
    .rec-item{background:var(--bg2);border:1px solid var(--border);border-radius:12px;padding:16px 18px;display:flex;gap:16px;align-items:flex-start;box-shadow:var(--shadow-sm)}
    .rec-number{width:30px;height:30px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:700;font-family:'JetBrains Mono',monospace;flex-shrink:0;background:var(--rec-bg,var(--yellow-dim));color:var(--rec-color,var(--yellow))}
    .rec-content{flex:1}
    .rec-title{font-size:14px;font-weight:600;color:var(--text);margin-bottom:4px}
    .rec-body{font-size:13px;color:var(--text-dim);line-height:1.5}
    .rec-priority{font-size:11px;padding:3px 10px;border-radius:99px;font-weight:600;flex-shrink:0;align-self:flex-start}

    /* Divider */
    .divider{display:flex;align-items:center;gap:12px;margin:36px 0 28px}
    .divider-line{flex:1;height:1px;background:var(--border)}
    .divider-label{font-size:11px;font-weight:600;letter-spacing:0.10em;text-transform:uppercase;color:var(--text-muted);white-space:nowrap}

    /* Footer */
    .report-footer{margin-top:60px;padding-top:24px;border-top:1px solid var(--border);display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px}
    .report-footer-brand{font-size:13px;font-weight:600;color:var(--text-muted);font-family:'JetBrains Mono',monospace}
    .report-footer-ts{font-size:12px;font-family:'JetBrains Mono',monospace;color:var(--text-muted)}

    /* Responsive */
    @media(max-width:900px){.hero{grid-template-columns:1fr}.score-ring-card{flex-direction:row;padding:20px 24px;justify-content:flex-start;gap:24px}.score-ring-desc{text-align:left}.stat-grid{grid-template-columns:repeat(2,1fr)}}
    @media(max-width:600px){.container{padding:48px 16px 60px}.report-title{font-size:26px}.metric-grid,.breakdown-grid{grid-template-columns:1fr}.info-grid{grid-template-columns:repeat(2,1fr)}.list-grid{grid-template-columns:1fr}.data-table th,.data-table td{padding:10px 12px}}
  </style>
</head>
<body>
  <div class="top-bar"></div>
  <button class="theme-toggle" id="themeBtn" onclick="toggleTheme()" aria-label="Toggle theme">&#127769;</button>
  <div class="container">

    <!-- 1. HEADER -->
    <header class="report-header anim anim-1">
      <div class="report-header-meta">
        <span class="report-eyebrow">System Health</span>
        <span class="status-badge badge-green">Healthy</span>
      </div>
      <h1 class="report-title">Kovo Health Report</h1>
      <p class="report-subtitle">kovo &middot; 10.0.1.133 &middot; Tuesday, 25 March 2026 &middot; 08:00 GST</p>
    </header>

    <!-- HERO: 2. SCORE RING + 3. STAT CARDS -->
    <!-- Score ring offset = 439.82 - (439.82 x score/100). Score 94 -> offset 26.39 -->
    <div class="hero anim anim-2">
      <div class="score-ring-card">
        <span class="score-ring-label">Health Score</span>
        <div class="score-ring-wrapper">
          <svg class="score-ring-svg" viewBox="0 0 160 160">
            <defs>
              <linearGradient id="ringGrad" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stop-color="#22d3ee"/>
                <stop offset="100%" stop-color="#4ade80"/>
              </linearGradient>
            </defs>
            <circle class="score-ring-track" cx="80" cy="80" r="70"/>
            <circle class="score-ring-fill" cx="80" cy="80" r="70" stroke="url(#ringGrad)" stroke-dashoffset="26.39"/>
          </svg>
          <div class="score-ring-value">
            <span class="score-ring-number" style="color:var(--cyan)">94</span>
            <span class="score-ring-unit">/100</span>
          </div>
        </div>
        <span class="score-ring-desc">All services nominal.<br>1 non-critical warning.</span>
      </div>
      <div class="stat-grid">
        <div class="stat-card" style="--accent:var(--cyan)">
          <div class="stat-card-value">99.8%</div>
          <div class="stat-card-label">Uptime (30d)</div>
          <div class="stat-card-sub">&#8593; 0.2% from last week</div>
        </div>
        <div class="stat-card" style="--accent:var(--green)">
          <div class="stat-card-value">4</div>
          <div class="stat-card-label">Services Running</div>
          <div class="stat-card-sub">0 degraded &middot; 0 stopped</div>
        </div>
        <div class="stat-card" style="--accent:var(--purple)">
          <div class="stat-card-value">247ms</div>
          <div class="stat-card-label">Avg Response</div>
          <div class="stat-card-sub">Gateway p95: 412ms</div>
        </div>
        <div class="stat-card" style="--accent:var(--orange)">
          <div class="stat-card-value">127</div>
          <div class="stat-card-label">Messages Today</div>
          <div class="stat-card-sub">&#8593; 18 from yesterday</div>
        </div>
      </div>
    </div>

    <!-- 13. SECTION DIVIDER -->
    <div class="divider anim anim-3"><div class="divider-line"></div><span class="divider-label">System Info</span><div class="divider-line"></div></div>

    <!-- 4. INFO GRID -->
    <div class="section anim anim-3">
      <div class="info-grid">
        <div class="info-item"><div class="info-item-key">Hostname</div><div class="info-item-value">kovo</div></div>
        <div class="info-item"><div class="info-item-key">IP Address</div><div class="info-item-value">10.0.1.133</div></div>
        <div class="info-item"><div class="info-item-key">OS</div><div class="info-item-value">Ubuntu 25.10</div></div>
        <div class="info-item"><div class="info-item-key">Gateway Port</div><div class="info-item-value">:8080</div></div>
        <div class="info-item"><div class="info-item-key">Ollama</div><div class="info-item-value">10.0.1.212:11434</div></div>
        <div class="info-item"><div class="info-item-key">Load (1m/5m/15m)</div><div class="info-item-value">0.42 / 0.38 / 0.35</div></div>
      </div>
    </div>

    <div class="divider anim anim-3"><div class="divider-line"></div><span class="divider-label">Resources</span><div class="divider-line"></div></div>

    <!-- 5. METRIC CARDS (lower=better: 0-30% green, 31-60% cyan, 61-80% yellow, 81-100% red) -->
    <div class="section anim anim-4">
      <div class="metric-grid">
        <div class="metric-card">
          <div class="metric-header"><span class="metric-name">CPU Usage</span><span class="metric-pct" style="color:var(--green)">23%</span></div>
          <div class="progress-track"><div class="progress-fill" style="width:23%;background:linear-gradient(90deg,var(--green),var(--cyan))"></div></div>
          <div class="metric-details">
            <div class="metric-detail-row"><span class="metric-detail-label">Cores</span><span class="metric-detail-val">4 vCPU</span></div>
            <div class="metric-detail-row"><span class="metric-detail-label">Load Avg</span><span class="metric-detail-val">0.42</span></div>
            <div class="metric-detail-row"><span class="metric-detail-label">User</span><span class="metric-detail-val">18%</span></div>
            <div class="metric-detail-row"><span class="metric-detail-label">Sys</span><span class="metric-detail-val">5%</span></div>
          </div>
        </div>
        <div class="metric-card">
          <div class="metric-header"><span class="metric-name">Memory</span><span class="metric-pct" style="color:var(--yellow)">61%</span></div>
          <div class="progress-track"><div class="progress-fill" style="width:61%;background:linear-gradient(90deg,var(--cyan),var(--yellow))"></div></div>
          <div class="metric-details">
            <div class="metric-detail-row"><span class="metric-detail-label">Used</span><span class="metric-detail-val">4.9 GB</span></div>
            <div class="metric-detail-row"><span class="metric-detail-label">Total</span><span class="metric-detail-val">8 GB</span></div>
            <div class="metric-detail-row"><span class="metric-detail-label">Cached</span><span class="metric-detail-val">1.2 GB</span></div>
            <div class="metric-detail-row"><span class="metric-detail-label">Free</span><span class="metric-detail-val">3.1 GB</span></div>
          </div>
        </div>
        <div class="metric-card">
          <div class="metric-header"><span class="metric-name">Disk (root)</span><span class="metric-pct" style="color:var(--green)">28%</span></div>
          <div class="progress-track"><div class="progress-fill" style="width:28%;background:linear-gradient(90deg,var(--green),var(--cyan))"></div></div>
          <div class="metric-details">
            <div class="metric-detail-row"><span class="metric-detail-label">Used</span><span class="metric-detail-val">14.0 GB</span></div>
            <div class="metric-detail-row"><span class="metric-detail-label">Total</span><span class="metric-detail-val">50 GB</span></div>
            <div class="metric-detail-row"><span class="metric-detail-label">Free</span><span class="metric-detail-val">36.0 GB</span></div>
            <div class="metric-detail-row"><span class="metric-detail-label">Inodes</span><span class="metric-detail-val">12%</span></div>
          </div>
        </div>
      </div>
    </div>

    <div class="divider anim anim-4"><div class="divider-line"></div><span class="divider-label">Services</span><div class="divider-line"></div></div>

    <!-- 6. DATA TABLE -->
    <div class="section anim anim-4">
      <div class="data-table-wrap">
        <table class="data-table">
          <thead><tr><th>Service</th><th>Status</th><th>PID</th><th>Memory</th><th>Uptime</th></tr></thead>
          <tbody>
            <tr><td><strong>Kovo Gateway</strong></td><td><span class="pill pill-green">Active</span></td><td class="mono">3821</td><td class="mono">312 MB</td><td class="mono">6d 14h</td></tr>
            <tr><td><strong>Redis</strong></td><td><span class="pill pill-green">Active</span></td><td class="mono">1204</td><td class="mono">18 MB</td><td class="mono">6d 14h</td></tr>
            <tr><td><strong>Heartbeat (APScheduler)</strong></td><td><span class="pill pill-green">Active</span></td><td class="mono">&mdash;</td><td class="mono">in-process</td><td class="mono">6d 14h</td></tr>
            <tr><td><strong>SSH</strong></td><td><span class="pill pill-green">Active</span></td><td class="mono">892</td><td class="mono">4 MB</td><td class="mono">6d 14h</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 7. LIST ROWS -->
    <div class="section anim anim-4">
      <div class="section-title">Network Connectivity</div>
      <div class="list-grid">
        <div class="list-row"><div><div class="list-row-label">Telegram API</div><div class="list-row-sub">api.telegram.org</div></div><span class="pill pill-green">Reachable</span></div>
        <div class="list-row"><div><div class="list-row-label">Ollama NUC</div><div class="list-row-sub">10.0.1.212:11434</div></div><span class="pill pill-yellow">Unreachable</span></div>
        <div class="list-row"><div><div class="list-row-label">Claude API</div><div class="list-row-sub">api.anthropic.com</div></div><span class="pill pill-green">Reachable</span></div>
        <div class="list-row"><div><div class="list-row-label">Google API</div><div class="list-row-sub">googleapis.com</div></div><span class="pill pill-cyan">Not Configured</span></div>
      </div>
    </div>

    <!-- 8. ITEM CARDS -->
    <div class="section anim anim-5">
      <div class="section-title">Software</div>
      <div class="item-card-grid">
        <div class="item-card"><div class="item-dot" style="background:var(--cyan)"></div><span class="item-label">Kovo</span><span class="item-badge">v1.4</span></div>
        <div class="item-card"><div class="item-dot" style="background:var(--green)"></div><span class="item-label">Python</span><span class="item-badge">3.13.2</span></div>
        <div class="item-card"><div class="item-dot" style="background:var(--green)"></div><span class="item-label">Node.js</span><span class="item-badge">22.14.0</span></div>
        <div class="item-card"><div class="item-dot" style="background:var(--purple)"></div><span class="item-label">FastAPI</span><span class="item-badge">0.115.x</span></div>
        <div class="item-card"><div class="item-dot" style="background:var(--orange)"></div><span class="item-label">claude-code</span><span class="item-badge">CLI</span></div>
        <div class="item-card"><div class="item-dot" style="background:var(--yellow)"></div><span class="item-label">llama3.1:8b</span><span class="item-badge">Ollama</span></div>
      </div>
    </div>

    <div class="divider anim anim-5"><div class="divider-line"></div><span class="divider-label">Component Scores</span><div class="divider-line"></div></div>

    <!-- 9. SCORE BREAKDOWN (higher=better: 90-100 green, 70-89 cyan, 50-69 yellow, 0-49 red) -->
    <!-- Sparkline: viewBox="0 0 160 40", y=0 is top, y=40 is bottom -->
    <div class="section anim anim-5">
      <div class="breakdown-grid">
        <div class="breakdown-card">
          <div class="breakdown-accent" style="--bd-color:var(--green)"></div>
          <div class="breakdown-body">
            <div class="breakdown-header"><span class="breakdown-name">Gateway</span><span class="breakdown-score" style="color:var(--green)">98</span></div>
            <div class="breakdown-progress"><div class="breakdown-progress-fill" style="width:98%;--bd-color:var(--green)"></div></div>
            <div class="breakdown-desc">FastAPI on :8080 &mdash; excellent response times, 0 errors in last 6h</div>
            <div class="sparkline-wrap">
              <svg class="sparkline" viewBox="0 0 160 40" preserveAspectRatio="none">
                <defs><linearGradient id="spk1" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#4ade80" stop-opacity="0.35"/><stop offset="100%" stop-color="#4ade80" stop-opacity="0"/></linearGradient></defs>
                <path d="M0,22 L26,16 L52,20 L78,6 L104,10 L130,3 L160,4" fill="none" stroke="#4ade80" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M0,22 L26,16 L52,20 L78,6 L104,10 L130,3 L160,4 L160,40 L0,40Z" fill="url(#spk1)"/>
              </svg>
            </div>
          </div>
        </div>
        <div class="breakdown-card">
          <div class="breakdown-accent" style="--bd-color:var(--cyan)"></div>
          <div class="breakdown-body">
            <div class="breakdown-header"><span class="breakdown-name">Memory System</span><span class="breakdown-score" style="color:var(--cyan)">84</span></div>
            <div class="breakdown-progress"><div class="breakdown-progress-fill" style="width:84%;--bd-color:var(--cyan)"></div></div>
            <div class="breakdown-desc">Daily logs active &mdash; MEMORY.md last flushed 2 days ago</div>
            <div class="sparkline-wrap">
              <svg class="sparkline" viewBox="0 0 160 40" preserveAspectRatio="none">
                <defs><linearGradient id="spk2" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#22d3ee" stop-opacity="0.35"/><stop offset="100%" stop-color="#22d3ee" stop-opacity="0"/></linearGradient></defs>
                <path d="M0,28 L26,22 L52,18 L78,24 L104,14 L130,10 L160,14" fill="none" stroke="#22d3ee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M0,28 L26,22 L52,18 L78,24 L104,14 L130,10 L160,14 L160,40 L0,40Z" fill="url(#spk2)"/>
              </svg>
            </div>
          </div>
        </div>
        <div class="breakdown-card">
          <div class="breakdown-accent" style="--bd-color:var(--cyan)"></div>
          <div class="breakdown-body">
            <div class="breakdown-header"><span class="breakdown-name">Heartbeat</span><span class="breakdown-score" style="color:var(--cyan)">72</span></div>
            <div class="breakdown-progress"><div class="breakdown-progress-fill" style="width:72%;--bd-color:var(--cyan)"></div></div>
            <div class="breakdown-desc">Scheduler running &mdash; Ollama unreachable, full checks skipped</div>
            <div class="sparkline-wrap">
              <svg class="sparkline" viewBox="0 0 160 40" preserveAspectRatio="none">
                <defs><linearGradient id="spk3" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#22d3ee" stop-opacity="0.35"/><stop offset="100%" stop-color="#22d3ee" stop-opacity="0"/></linearGradient></defs>
                <path d="M0,16 L26,22 L52,14 L78,18 L104,24 L130,16 L160,20" fill="none" stroke="#22d3ee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M0,16 L26,22 L52,14 L78,18 L104,24 L130,16 L160,20 L160,40 L0,40Z" fill="url(#spk3)"/>
              </svg>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="divider anim anim-5"><div class="divider-line"></div><span class="divider-label">Recent Events</span><div class="divider-line"></div></div>

    <!-- 10. TIMELINE (--tl-color sets dot border) -->
    <div class="section anim anim-5">
      <div class="timeline">
        <div class="timeline-item">
          <div class="timeline-left"><div class="timeline-dot" style="--tl-color:var(--green)"></div><div class="timeline-line"></div></div>
          <div class="timeline-content"><div class="timeline-time">08:00 GST &middot; Today</div><div class="timeline-title">Morning briefing sent</div><div class="timeline-body">Daily summary delivered via Telegram. 127 messages processed yesterday.</div></div>
        </div>
        <div class="timeline-item">
          <div class="timeline-left"><div class="timeline-dot" style="--tl-color:var(--cyan)"></div><div class="timeline-line"></div></div>
          <div class="timeline-content"><div class="timeline-time">02:00 GST &middot; Today</div><div class="timeline-title">Auto-purge completed</div><div class="timeline-body">Cleared 340 MB of old temp files and audio clips. No user files touched.</div></div>
        </div>
        <div class="timeline-item">
          <div class="timeline-left"><div class="timeline-dot" style="--tl-color:var(--yellow)"></div><div class="timeline-line"></div></div>
          <div class="timeline-content"><div class="timeline-time">Yesterday &middot; 18:32 GST</div><div class="timeline-title">Ollama connectivity lost</div><div class="timeline-body">NUC at 10.0.1.212 unreachable &mdash; heartbeat health checks skipped. Non-fatal.</div></div>
        </div>
        <div class="timeline-item">
          <div class="timeline-left"><div class="timeline-dot" style="--tl-color:var(--purple)"></div><div class="timeline-line"></div></div>
          <div class="timeline-content"><div class="timeline-time">2 days ago &middot; 09:15 GST</div><div class="timeline-title">Kovo v1.4 deployed</div><div class="timeline-body">Storage management, onboarding flow, and permission system added.</div></div>
        </div>
      </div>
    </div>

    <div class="divider anim anim-6"><div class="divider-line"></div><span class="divider-label">Activity</span><div class="divider-line"></div></div>

    <!-- 11. TAG CARDS (--tag-color sets top border and value color) -->
    <div class="section anim anim-6">
      <div class="tag-grid">
        <div class="tag-card" style="--tag-color:var(--cyan)"><span class="tag-card-value">127</span><div class="tag-card-label">Messages</div></div>
        <div class="tag-card" style="--tag-color:var(--green)"><span class="tag-card-value">14</span><div class="tag-card-label">Shell Cmds</div></div>
        <div class="tag-card" style="--tag-color:var(--purple)"><span class="tag-card-value">3</span><div class="tag-card-label">Skills Used</div></div>
        <div class="tag-card" style="--tag-color:var(--orange)"><span class="tag-card-value">7</span><div class="tag-card-label">Files Created</div></div>
        <div class="tag-card" style="--tag-color:var(--yellow)"><span class="tag-card-value">2</span><div class="tag-card-label">Warnings</div></div>
        <div class="tag-card" style="--tag-color:var(--green)"><span class="tag-card-value">0</span><div class="tag-card-label">Errors</div></div>
      </div>
    </div>

    <div class="divider anim anim-6"><div class="divider-line"></div><span class="divider-label">Recommendations</span><div class="divider-line"></div></div>

    <!-- 12. NUMBERED RECOMMENDATIONS (--rec-bg/--rec-color style the number badge) -->
    <div class="section anim anim-6">
      <div class="rec-list">
        <div class="rec-item">
          <div class="rec-number" style="--rec-bg:var(--yellow-dim);--rec-color:var(--yellow)">1</div>
          <div class="rec-content"><div class="rec-title">Restore Ollama connectivity</div><div class="rec-body">NUC at 10.0.1.212 has been unreachable for 14 hours. Heartbeat health checks and model routing are degraded. Check NUC power and network.</div></div>
          <span class="rec-priority pill pill-yellow">Medium</span>
        </div>
        <div class="rec-item">
          <div class="rec-number" style="--rec-bg:var(--cyan-dim);--rec-color:var(--cyan)">2</div>
          <div class="rec-content"><div class="rec-title">Flush MEMORY.md</div><div class="rec-body">Long-term memory hasn't been updated in 2 days. Run /flush to summarize this week's activity into MEMORY.md before the weekly digest.</div></div>
          <span class="rec-priority pill pill-cyan">Low</span>
        </div>
        <div class="rec-item">
          <div class="rec-number" style="--rec-bg:var(--green-dim);--rec-color:var(--green)">3</div>
          <div class="rec-content"><div class="rec-title">All good &mdash; 36 GB disk free</div><div class="rec-body">Disk usage is at 28%, well within safe range. Auto-purge cleared 340 MB overnight. No action needed.</div></div>
          <span class="rec-priority pill pill-green">Info</span>
        </div>
      </div>
    </div>

    <footer class="report-footer anim anim-7">
      <span class="report-footer-brand">Kovo &middot; Report Builder</span>
      <span class="report-footer-ts">Generated: 2026-03-25 08:00:12 GST</span>
    </footer>
  </div>

  <script>
    const THEME_KEY='kovo-report-theme';
    const btn=document.getElementById('themeBtn');
    function applyTheme(t){document.documentElement.setAttribute('data-theme',t);btn.textContent=t==='dark'?'&#127769;':'&#9728;&#65039;'}
    function toggleTheme(){const cur=document.documentElement.getAttribute('data-theme')||'dark';const next=cur==='dark'?'light':'dark';localStorage.setItem(THEME_KEY,next);applyTheme(next)}
    const saved=localStorage.getItem(THEME_KEY);if(saved)applyTheme(saved);
  </script>
</body>
</html>
HTMLEOF
ok "report-builder/templates/report-template.html written"

# --- TOOLS.md ---
cat > "$WORKSPACE/TOOLS.md" << 'EOF'
---
tools:
- config_needed: null
  description: Execute shell commands on the VM (file ops, installs, services)
  install_command: null
  name: shell
  status: configured
- config_needed: null
  description: Playwright headless browser automation (scraping, screenshots, web
    interaction)
  install_command: playwright install chromium
  name: browser
  status: configured
- config_needed: Configure via /auth_google in Telegram
  description: Google Docs, Drive, and Gmail integration via OAuth2
  install_command: null
  name: google_api
  status: not_configured
- config_needed: Set TELEGRAM_API_ID and TELEGRAM_API_HASH in config/.env
  description: Telegram voice calls + voice messages via Pyrogram userbot
  install_command: null
  name: telegram_call
  status: not_configured
- config_needed: null
  description: Text-to-speech using edge-tts (Microsoft voices, free)
  install_command: pip install edge-tts
  name: tts
  status: configured
- config_needed: null
  description: "Background heartbeat health checks only \u2014 Ollama on NUC at 10.0.1.212:11434"
  install_command: null
  name: ollama
  status: configured
- config_needed: Run claude setup-token to authenticate
  description: Claude Code CLI subprocess for complex reasoning (Sonnet/Opus)
  install_command: npm install -g @anthropic-ai/claude-code
  name: claude_cli
  status: not_configured
- config_needed: Set GROQ_API_KEY in config/.env
  description: Groq Whisper cloud transcription with local Whisper fallback
  install_command: pip install openai-whisper --no-deps && pip install torch --index-url
    https://download.pytorch.org/whl/cpu
  name: whisper
  status: not_configured
- config_needed: Set GITHUB_TOKEN in config/.env, then run /auth_github
  description: GitHub repos, issues, pull requests, file management, and code search
    via PyGithub
  install_command: pip install PyGithub
  name: github
  status: not_configured
---

# Tool Registry

This file tracks all tools available to Kovo and its sub-agents.
Agents check this registry before using a tool and notify Esam if a tool is missing or unconfigured.

## Status Values
- `installed` — tool is installed and ready to use
- `not_installed` — tool needs to be installed (`install_command` tells how)
- `configured` — tool is installed and fully configured
- `not_configured` — tool is installed but needs configuration (`config_needed` tells what)

## Environment
- **OS**: Ubuntu 25.10 (Questing) — VM on Unraid (8GB RAM, 50GB disk)
- **Python**: 3.13 (venv at /opt/kovo/venv)
- **Node**: 22+ (system install)
- **Workspace**: /opt/kovo/workspace

## Network Hosts
- **Ollama**: http://10.0.1.212:11434
- **Home Assistant**: (configure when ready)
- **Unraid WebUI**: (configure when ready)

## Tool Notes
- **shell**: Always available. Dangerous commands require Esam's Telegram confirmation.
- **browser**: Playwright with Chromium in headless mode.
- **google_api**: Requires OAuth2. Run `/auth_google` in Telegram to configure.
- **telegram_call**: Pyrogram userbot. Falls back to voice message if call not answered.
- **tts**: edge-tts (Microsoft Azure voices, free).
- **ollama**: Background heartbeat health checks only. Runs on NUC at 10.0.1.212:11434.
- **claude_cli**: Uses Esam's Claude Max subscription. No API key needed — authenticate with `claude setup-token`.
- **whisper**: Groq whisper-large-v3-turbo (primary) + local Whisper (fallback).
- **github**: PyGithub. Set GITHUB_TOKEN in config/.env. Run `/auth_github` to verify.
EOF
ok "TOOLS.md written"

# --- settings.yaml ---
cat > "$KOVO_DIR/config/settings.yaml" << 'EOF'
kovo:
  workspace: /opt/kovo/workspace
  data_dir: /opt/kovo/data
  log_dir: /opt/kovo/logs

telegram:
  token: ${TELEGRAM_BOT_TOKEN}
  allowed_users:
    - ${OWNER_TELEGRAM_ID}

ollama:
  url: http://10.0.1.212:11434
  default_model: llama3.1:8b

claude:
  default_model: sonnet
  memory_flush_model: sonnet
  timeout: 300

telegram_call:
  api_id: ${TELEGRAM_API_ID}
  api_hash: ${TELEGRAM_API_HASH}
  session_name: kovo_caller
  owner_user_id: ${OWNER_TELEGRAM_ID}
  call_timeout: 30
  tts:
    backend: edge-tts
    voice: en-US-AvaMultilingualNeural

google:
  credentials_file: /opt/kovo/config/google-credentials.json
  scopes:
    - https://www.googleapis.com/auth/drive
    - https://www.googleapis.com/auth/documents
    - https://www.googleapis.com/auth/gmail.modify
    - https://www.googleapis.com/auth/calendar
    - https://www.googleapis.com/auth/spreadsheets

heartbeat:
  quick_interval: 30   # minutes
  full_interval: 6     # hours
  morning_time: "08:00"
  use_ollama: true

transcription:
  groq_api_key: ${GROQ_API_KEY}
  whisper_model: base   # fallback local model: tiny, base, small, medium

dashboard:
  port: 3000  # Vite dev server only — production dashboard served by gateway at port 8080
  host: 0.0.0.0

gateway:
  port: 8080
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
    db_path: /opt/kovo/data/kovo.db
    max_db_size_mb: 100
    custom_table_prefix: "user_"
    schema_in_prompt: "on_demand"
EOF
ok "settings.yaml written"

# --- .env.template ---
cat > "$KOVO_DIR/config/.env.template" << 'EOF'
# Kovo Environment Variables
# Copy this to .env and fill in your values:
#   cp /opt/kovo/config/.env.template /opt/kovo/config/.env
#   nano /opt/kovo/config/.env

# ── Telegram Bot ──────────────────────────────────────────────────────────────
# Create a bot at https://t.me/BotFather → /newbot
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# Your personal Telegram user ID (find via @userinfobot)
OWNER_TELEGRAM_ID=your_telegram_user_id_here

# ── Telegram Userbot (voice calls) ────────────────────────────────────────────
# Get from https://my.telegram.org → API development tools
TELEGRAM_API_ID=your_api_id_here
TELEGRAM_API_HASH=your_api_hash_here

# ── Claude Code ───────────────────────────────────────────────────────────────
# Authenticate with: claude setup-token
# Then paste the token here
CLAUDE_CODE_OAUTH_TOKEN=your_claude_oauth_token_here

# ── Groq (Whisper transcription) ─────────────────────────────────────────────
# Free tier at https://console.groq.com
GROQ_API_KEY=your_groq_api_key_here

# ── GitHub ────────────────────────────────────────────────────────────────────
# Personal access token at https://github.com/settings/tokens
# Scopes needed: repo, read:user
GITHUB_TOKEN=your_github_token_here

# ── Google OAuth ──────────────────────────────────────────────────────────────
# Path to OAuth2 credentials JSON from Google Cloud Console
GOOGLE_CREDENTIALS_PATH=/opt/kovo/config/google-credentials.json

# ── Optional: ElevenLabs TTS ─────────────────────────────────────────────────
# Leave empty to use edge-tts (free, Microsoft voices)
# ELEVENLABS_API_KEY=
EOF
ok ".env.template written"

# --- Secure file permissions ---
chmod 600 "$KOVO_DIR/config/.env.template"
chmod 700 "$KOVO_DIR/config"
[ -f "$KOVO_DIR/config/.env" ]                          && chmod 600 "$KOVO_DIR/config/.env"
[ -f "$KOVO_DIR/config/google-credentials.json" ]       && chmod 600 "$KOVO_DIR/config/google-credentials.json"
[ -f "$KOVO_DIR/data/kovo.db" ]                     && chmod 600 "$KOVO_DIR/data/kovo.db"
[ -f "$KOVO_DIR/.claude/settings.local.json" ]          && chmod 600 "$KOVO_DIR/.claude/settings.local.json"
ok "file permissions secured (600/700)"

# --- logrotate config ---
if [ ! -f /etc/logrotate.d/kovo ]; then
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
    ok "logrotate config created"
else
    ok "logrotate config already exists (skipping)"
fi

# --- scripts/backup.sh ---
cat > "$KOVO_DIR/scripts/backup.sh" << 'EOF'
#!/bin/bash
WORKSPACE="/opt/kovo/workspace"
BACKUP_DIR="/opt/kovo/data/backups"
DATE=$(date +%Y%m%d)
mkdir -p "$BACKUP_DIR"
tar czf "$BACKUP_DIR/workspace_$DATE.tar.gz" -C /opt/kovo workspace/
# Also back up the security baseline
[ -f /opt/kovo/data/security_baseline.json ] && \
    cp /opt/kovo/data/security_baseline.json "$BACKUP_DIR/security_baseline_$DATE.json"
find "$BACKUP_DIR" -name "workspace_*.tar.gz" -mtime +30 -delete
find "$BACKUP_DIR" -name "security_baseline_*.json" -mtime +30 -delete
echo "Backup: $BACKUP_DIR/workspace_$DATE.tar.gz"
EOF
chmod +x "$KOVO_DIR/scripts/backup.sh"
ok "scripts/backup.sh written"

# --- scripts/migrate_openclaw.sh ---
cat > "$KOVO_DIR/scripts/migrate_openclaw.sh" << 'EOF'
#!/bin/bash
# Migrate OpenClaw workspace to Kovo
# Usage: ./migrate_openclaw.sh /path/to/openclaw/workspace

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 /path/to/openclaw/workspace"
    exit 1
fi

SOURCE="$1"
TARGET="/opt/kovo/workspace"

echo "Migrating OpenClaw workspace from: $SOURCE"
echo "To: $TARGET"
echo ""

# Backup existing workspace
if [ -d "$TARGET" ] && [ "$(ls -A $TARGET)" ]; then
    BACKUP="$TARGET.backup.$(date +%Y%m%d_%H%M%S)"
    echo "Backing up existing workspace to $BACKUP"
    cp -r "$TARGET" "$BACKUP"
fi

# Direct copy files
for f in SOUL.md USER.md MEMORY.md IDENTITY.md HEARTBEAT.md; do
    if [ -f "$SOURCE/$f" ]; then
        cp "$SOURCE/$f" "$TARGET/$f"
        echo "  ✓ Copied $f"
    else
        echo "  ⊘ $f not found (keeping default)"
    fi
done

# Copy with notes
if [ -f "$SOURCE/TOOLS.md" ]; then
    cp "$SOURCE/TOOLS.md" "$TARGET/TOOLS.md"
    echo -e "\n## Kovo Migration Notes\n- Migrated from OpenClaw on $(date)\n- Update paths and hosts for VM" >> "$TARGET/TOOLS.md"
    echo "  ✓ Copied TOOLS.md (review paths!)"
fi

if [ -f "$SOURCE/AGENTS.md" ]; then
    cp "$SOURCE/AGENTS.md" "$TARGET/AGENTS.md"
    echo "  ✓ Copied AGENTS.md (review boot sequence)"
fi

# Copy directories
for dir in memory skills checklists docs; do
    if [ -d "$SOURCE/$dir" ]; then
        cp -r "$SOURCE/$dir/"* "$TARGET/$dir/" 2>/dev/null || true
        echo "  ✓ Copied $dir/"
    fi
done

echo ""
echo "✅ Migration complete! Review TOOLS.md and AGENTS.md for path updates."
EOF
chmod +x "$KOVO_DIR/scripts/migrate_openclaw.sh"
ok "scripts/migrate_openclaw.sh written"

# --- CLAUDE.md (copy from /tmp if present) ---
if [ -f /tmp/CLAUDE.md ]; then
    cp /tmp/CLAUDE.md "$KOVO_DIR/CLAUDE.md"
    ok "CLAUDE.md copied from /tmp/CLAUDE.md"
else
    warn "CLAUDE.md not found at /tmp/CLAUDE.md — place it manually at $KOVO_DIR/CLAUDE.md"
fi

# ============================================================
# Step 16/16: Systemd service
# ============================================================
step "16/16 — Systemd service"

SYSTEMD_CONTENT="[Unit]
Description=Kovo AI Agent
After=network.target redis.service
Wants=redis.service

[Service]
Type=simple
User=${USER}
WorkingDirectory=/opt/kovo
EnvironmentFile=/opt/kovo/config/.env
ExecStart=/opt/kovo/venv/bin/python -m uvicorn src.gateway.main:app --host 0.0.0.0 --port 8080 --log-level info
Restart=always
RestartSec=5
TimeoutStopSec=30
StandardOutput=append:/opt/kovo/logs/gateway.log
StandardError=append:/opt/kovo/logs/gateway.log

[Install]
WantedBy=multi-user.target"

echo "$SYSTEMD_CONTENT" | sudo tee /etc/systemd/system/kovo.service > /dev/null
echo "$SYSTEMD_CONTENT" > "$KOVO_DIR/systemd/kovo.service"
sudo systemctl daemon-reload
ok "Systemd service written (User=$USER, TimeoutStopSec=30, RestartSec=5)"

# ============================================================
# Verification
# ============================================================
echo ""
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo -e "${GREEN}  Verification                          ${NC}"
echo -e "${GREEN}════════════════════════════════════════${NC}"

VERIFY_ERRORS=0

check() {
    local label="$1"
    local cmd="$2"
    if eval "$cmd" &>/dev/null; then
        ok "$label"
    else
        fail "$label"
        VERIFY_ERRORS=$((VERIFY_ERRORS + 1))
    fi
}

check "python3.13"              "python3 --version | grep -q '3.13'"
check "node 22+"               "node --version | grep -qE 'v2[2-9]'"
check "npm"                    "npm --version"
check "claude CLI"             "command -v claude"
check "redis running"          "redis-cli ping | grep -q PONG"
check "venv exists"            "[ -d $VENV ]"
check "venv/python"            "[ -f $VENV/bin/python ]"
check "PyTorch installed"      "$VENV/bin/python -c 'import torch'"
check "FastAPI installed"      "$VENV/bin/python -c 'import fastapi'"
check "python-telegram-bot"    "$VENV/bin/python -c 'import telegram'"
check "Playwright installed"   "$VENV/bin/python -c 'import playwright'"
check "Chromium installed"     "[ -d $HOME/.cache/ms-playwright ]"
check "ffmpeg"                 "command -v ffmpeg"
check "SOUL.md exists"         "[ -f $WORKSPACE/SOUL.md ]"
check "UNCONFIGURED marker"    "grep -q '## UNCONFIGURED' $WORKSPACE/SOUL.md"
check "settings.yaml"          "[ -f $KOVO_DIR/config/settings.yaml ]"
check ".env.template"          "[ -f $KOVO_DIR/config/.env.template ]"
check ".env.template perms"   "[ \"\$(stat -c %a $KOVO_DIR/config/.env.template)\" = '600' ]"
check "config dir perms"      "[ \"\$(stat -c %a $KOVO_DIR/config)\" = '700' ]"
check "permissions JSON"       "[ -f $KOVO_DIR/.claude/settings.local.json ]"
check "systemd service"        "[ -f /etc/systemd/system/kovo.service ]"
check "backup.sh"              "[ -x $KOVO_DIR/scripts/backup.sh ]"
check "data/tmp dir"           "[ -d $KOVO_DIR/data/tmp ]"
check "data/audio dir"         "[ -d $KOVO_DIR/data/audio ]"
check "data/backups dir"       "[ -d $KOVO_DIR/data/backups ]"
check "SQLite DB placeholder"  "[ -f $KOVO_DIR/data/kovo.db ]"
check "memory archive dir"     "[ -d $WORKSPACE/memory/archive ]"
check "ClamAV installed"       "command -v clamscan"
check "chkrootkit installed"   "command -v chkrootkit"
check "rkhunter installed"     "command -v rkhunter"
check "security-audit skill"   "[ -f $WORKSPACE/skills/security-audit/SKILL.md ]"

# Disk space check
FREE_KB=$(df /opt --output=avail | tail -1)
FREE_GB=$((FREE_KB / 1048576))
if [ "$FREE_GB" -ge 10 ]; then
    ok "Disk space: ${FREE_GB}GB free"
else
    warn "Low disk space: only ${FREE_GB}GB free (recommend 20GB+)"
fi

# Ollama connectivity (non-fatal)
if curl -sf --max-time 3 http://10.0.1.212:11434/api/version &>/dev/null; then
    ok "Ollama reachable at 10.0.1.212:11434"
else
    warn "Ollama not reachable at 10.0.1.212:11434 (heartbeats will fail until NUC is up)"
fi

# ============================================================
# Summary
# ============================================================
echo ""
echo -e "${GREEN}════════════════════════════════════════${NC}"
if [ "$VERIFY_ERRORS" -eq 0 ]; then
    echo -e "${GREEN}  ✅ Bootstrap complete — all checks passed${NC}"
else
    echo -e "${YELLOW}  ⚠️  Bootstrap complete — $VERIFY_ERRORS check(s) failed${NC}"
fi
echo -e "${GREEN}════════════════════════════════════════${NC}"

# ============================================================
# Next steps
# ============================================================
echo ""
echo -e "${GREEN}Next Steps:${NC}"
echo ""
echo "  1. Authenticate Claude Code:"
echo "       claude setup-token"
echo "     (Opens URL → authorize → paste the token when prompted)"
echo "     Then set it in your env:"
echo "       echo 'export CLAUDE_CODE_OAUTH_TOKEN=YOUR_TOKEN' >> ~/.bashrc && source ~/.bashrc"
echo ""
echo "  2. Set up .env:"
echo "       cp $KOVO_DIR/config/.env.template $KOVO_DIR/config/.env"
echo "       nano $KOVO_DIR/config/.env"
echo "     (Fill in: TELEGRAM_BOT_TOKEN, OWNER_TELEGRAM_ID, GROQ_API_KEY, etc.)"
echo "     File is auto-secured (chmod 600, owner-only read/write)"
echo ""
echo "  3. Kovo is ready! Start the service:"
echo "       sudo systemctl daemon-reload"
echo "       sudo systemctl enable --now kovo"
echo "       sudo systemctl status kovo"
echo ""
echo "  4. Open Telegram and send a message to your bot."
echo "     The onboarding flow will personalise your agent's name and personality."
echo ""
echo "  Dashboard: http://$(hostname -I | awk '{print $1}'):8080"
echo ""
echo "  Optional integrations (run in Telegram after service is up):"
echo "    /reauth_caller +YOURNUMBER   — voice call support"
echo "    /auth_google                 — Google Docs/Drive/Gmail"
echo "    /auth_github                 — GitHub integration"
echo ""
echo "  Useful commands:"
echo "    sudo journalctl -fu kovo           — follow service logs"
echo "    sudo systemctl restart kovo        — restart service"
echo "    $KOVO_DIR/scripts/backup.sh        — manual workspace backup"
echo ""
