#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# KOVO Restore — Restores a backup archive
# Called by the API or manually.
#
# Usage:
#   bash restore.sh /path/to/kovo-backup-core_20260927.tar.gz
# ═══════════════════════════════════════════════════════════════════
set -e

# ─── Cross-platform KOVO_DIR detection ────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -n "${KOVO_DIR:-}" ]; then
    : # already set
elif [ -f "$SCRIPT_DIR/../bootstrap.sh" ]; then
    KOVO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
elif [ -d "/opt/kovo" ]; then
    KOVO_DIR="/opt/kovo"
elif [ -d "$HOME/.kovo" ]; then
    KOVO_DIR="$HOME/.kovo"
else
    echo "ERROR: Cannot find KOVO installation"; exit 1
fi

OS_TYPE="$(uname -s)"
ARCHIVE="$1"

G='\033[38;5;114m' B='\033[38;5;75m' Y='\033[38;5;221m'
R='\033[38;5;203m' D='\033[2m' N='\033[0m' W='\033[38;5;255m'

ok()   { echo -e "  ${G}✓${N} $1"; }
info() { echo -e "  ${B}→${N} $1"; }
warn() { echo -e "  ${Y}⚠${N} $1"; }
fail() { echo -e "  ${R}✗${N} $1"; }

if [ -z "$ARCHIVE" ] || [ ! -f "$ARCHIVE" ]; then
    fail "Usage: bash restore.sh /path/to/backup.tar.gz"
    exit 1
fi

echo ""
echo -e "  ${B}KOVO Restore${N}"
echo ""

# ─── Extract to staging ──────────────────────────────────────────
STAGE="/tmp/kovo-restore-$$"
mkdir -p "$STAGE"
info "Extracting backup..."
tar xzf "$ARCHIVE" -C "$STAGE"

# ─── Read manifest ───────────────────────────────────────────────
if [ -f "$STAGE/manifest.json" ]; then
    ok "Manifest found"
    python3 -c "
import json
with open('$STAGE/manifest.json') as f:
    m = json.load(f)
print(f\"  Version:  {m.get('kovo_version', '?')}\")
print(f\"  Date:     {m.get('backup_date', '?')}\")
print(f\"  Host:     {m.get('hostname', '?')}\")
print(f\"  Memory:   {m.get('stats', {}).get('memory_days', 0)} days\")
print(f\"  Skills:   {m.get('stats', {}).get('skills_count', 0)}\")
print(f\"  Pip pkgs: {m.get('stats', {}).get('pip_delta_count', 0)} user-added\")
"
    echo ""
else
    warn "No manifest.json — legacy backup format"
fi

# ─── Restore config ──────────────────────────────────────────────
info "Restoring config & auth..."
if [ -d "$STAGE/config" ]; then
    # Merge .env: keep new machine's values for anything already set,
    # add missing values from backup
    if [ -f "$STAGE/config/.env" ] && [ -f "$KOVO_DIR/config/.env" ]; then
        python3 << MERGE_EOF
import os

def parse_env(path):
    env = {}
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    env[k.strip()] = v.strip()
    return env

backup_env = parse_env('$STAGE/config/.env')
current_env = parse_env('$KOVO_DIR/config/.env')

# Merge: backup fills in blanks, current overrides
merged = {**backup_env, **{k: v for k, v in current_env.items() if v}}

with open('$KOVO_DIR/config/.env', 'w') as f:
    for k, v in sorted(merged.items()):
        f.write(f'{k}={v}\n')

added = set(backup_env.keys()) - set(current_env.keys())
if added:
    print(f'  Added {len(added)} new env vars from backup: {", ".join(sorted(added))}')
MERGE_EOF
        ok ".env merged (backup fills blanks, current wins conflicts)"
    elif [ -f "$STAGE/config/.env" ]; then
        cp "$STAGE/config/.env" "$KOVO_DIR/config/.env"
        ok ".env restored from backup"
    fi

    # Other config files — just overlay
    for f in settings.yaml google-credentials.json google-token.json .env.template; do
        if [ -f "$STAGE/config/$f" ]; then
            cp "$STAGE/config/$f" "$KOVO_DIR/config/$f"
            ok "config/$f"
        fi
    done

    # Session files
    for f in "$STAGE"/config/*.session; do
        [ -f "$f" ] && cp "$f" "$KOVO_DIR/config/" && ok "session: $(basename $f)"
    done
fi

# Root-level session files
for f in "$STAGE"/*.session; do
    [ -f "$f" ] && cp "$f" "$KOVO_DIR/" && ok "session: $(basename $f)"
done

# Claude Code permissions
if [ -f "$STAGE/.claude/settings.local.json" ]; then
    mkdir -p "$KOVO_DIR/.claude"
    cp "$STAGE/.claude/settings.local.json" "$KOVO_DIR/.claude/"
    ok ".claude/settings.local.json"
fi

# ─── Restore brain ───────────────────────────────────────────────
info "Restoring brain & workspace..."
if [ -d "$STAGE/workspace" ]; then
    # Overlay workspace — don't delete existing files, just add/update
    cp -a "$STAGE/workspace/"* "$KOVO_DIR/workspace/" 2>/dev/null
    skills=$(find "$KOVO_DIR/workspace/skills" -name "SKILL.md" 2>/dev/null | wc -l)
    memory=$(find "$KOVO_DIR/workspace/memory" -name "*.md" 2>/dev/null | wc -l)
    ok "workspace ($skills skills, $memory memory files)"
fi

if [ -f "$STAGE/data/kovo.db" ]; then
    cp "$STAGE/data/kovo.db" "$KOVO_DIR/data/kovo.db"
    ok "kovo.db"
fi

if [ -d "$STAGE/data/security" ]; then
    mkdir -p "$KOVO_DIR/data/security"
    cp -a "$STAGE/data/security/"* "$KOVO_DIR/data/security/" 2>/dev/null
    ok "security data"
fi

if [ -d "$STAGE/scripts/experiments" ]; then
    mkdir -p "$KOVO_DIR/scripts/experiments"
    cp -a "$STAGE/scripts/experiments/"* "$KOVO_DIR/scripts/experiments/" 2>/dev/null
    ok "custom scripts"
fi

# ─── Restore packages ────────────────────────────────────────────
info "Reinstalling user-added packages..."
if [ -f "$STAGE/packages/pip_delta.txt" ] && [ -s "$STAGE/packages/pip_delta.txt" ]; then
    delta_count=$(wc -l < "$STAGE/packages/pip_delta.txt" | tr -d ' ')
    info "Installing $delta_count user-added Python packages..."
    "$KOVO_DIR/venv/bin/pip" install -r "$STAGE/packages/pip_delta.txt" -q 2>&1 | tail -3
    ok "pip: $delta_count packages reinstalled"
else
    ok "pip: no user-added packages to install"
fi

# Restore crontab
if [ -f "$STAGE/packages/crontab.txt" ] && [ -s "$STAGE/packages/crontab.txt" ]; then
    crontab "$STAGE/packages/crontab.txt"
    ok "crontab restored"
fi

# ─── Restore media ───────────────────────────────────────────────
for d in photos documents images screenshots audio; do
    if [ -d "$STAGE/data/$d" ]; then
        mkdir -p "$KOVO_DIR/data/$d"
        cp -a "$STAGE/data/$d/"* "$KOVO_DIR/data/$d/" 2>/dev/null
        count=$(find "$KOVO_DIR/data/$d" -type f | wc -l)
        ok "media: $d ($count files)"
    fi
done

# ─── Fix permissions ─────────────────────────────────────────────
info "Fixing permissions..."
chmod 700 "$KOVO_DIR/config" 2>/dev/null
chmod 600 "$KOVO_DIR/config/.env" 2>/dev/null
chmod 600 "$KOVO_DIR/config/google-credentials.json" 2>/dev/null
chmod 600 "$KOVO_DIR/config/google-token.json" 2>/dev/null
chmod 600 "$KOVO_DIR/.claude/settings.local.json" 2>/dev/null
chmod 600 "$KOVO_DIR/data/kovo.db" 2>/dev/null
for f in "$KOVO_DIR"/*.session "$KOVO_DIR"/config/*.session; do
    [ -f "$f" ] && chmod 600 "$f"
done
ok "permissions secured"

# ─── Cleanup ──────────────────────────────────────────────────────
rm -rf "$STAGE"

# ─── Report ───────────────────────────────────────────────────────
echo ""
echo -e "  ${G}╔═══════════════════════════════════════════════╗${N}"
echo -e "  ${G}║          Restore Complete!                    ║${N}"
echo -e "  ${G}╚═══════════════════════════════════════════════╝${N}"
echo ""

# Check what needs re-auth
echo -e "  ${W}Auth status:${N}"
if grep -q "TELEGRAM_BOT_TOKEN=." "$KOVO_DIR/config/.env" 2>/dev/null; then
    echo -e "    ${G}✓${N} Telegram bot token"
else
    echo -e "    ${R}✗${N} Telegram bot token — set in dashboard"
fi

if ls "$KOVO_DIR"/*.session "$KOVO_DIR"/config/*.session 2>/dev/null | head -1 > /dev/null 2>&1; then
    echo -e "    ${G}✓${N} Telegram caller session"
else
    echo -e "    ${Y}⚠${N} Telegram caller session — run /reauth_caller if voice calls needed"
fi

if [ -f "$KOVO_DIR/config/google-token.json" ]; then
    echo -e "    ${G}✓${N} Google OAuth token"
else
    echo -e "    ${Y}⚠${N} Google OAuth — run /auth_google if needed"
fi

echo -e "    ${Y}⚠${N} Claude Code — run: ${W}claude login${N}"

if grep -q "GROQ_API_KEY=." "$KOVO_DIR/config/.env" 2>/dev/null; then
    echo -e "    ${G}✓${N} Groq API key"
fi

if grep -q "GITHUB_TOKEN=." "$KOVO_DIR/config/.env" 2>/dev/null; then
    echo -e "    ${G}✓${N} GitHub token"
fi

echo ""
if [ "$OS_TYPE" = "Darwin" ]; then
    echo -e "  ${D}Next: launchctl unload ~/Library/LaunchAgents/com.kovo.agent.plist && launchctl load ~/Library/LaunchAgents/com.kovo.agent.plist${N}"
else
    echo -e "  ${D}Next: sudo systemctl restart kovo${N}"
fi
echo ""
