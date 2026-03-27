#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# KOVO Backup v2 — Full Migration-Ready Backup
# Creates a single .tar.gz with everything needed to restore
# on a fresh machine with zero setup headaches.
#
# Usage:
#   bash backup.sh              # Core only (~1-5 MB)
#   bash backup.sh --full       # Core + media files (~1-10 GB)
#   bash backup.sh --list       # Show what would be backed up
# ═══════════════════════════════════════════════════════════════════
set -e

KOVO_DIR="/opt/kovo"
BACKUP_DIR="$KOVO_DIR/data/backups"
DATE=$(date +%Y%m%d_%H%M%S)
STAGE="/tmp/kovo-backup-$DATE"
INCLUDE_MEDIA=false
LIST_ONLY=false
RETENTION_DAYS=30

for arg in "$@"; do
    case "$arg" in
        --full)    INCLUDE_MEDIA=true ;;
        --list)    LIST_ONLY=true ;;
        --help|-h) echo "Usage: bash backup.sh [--full] [--list]"; exit 0 ;;
    esac
done

# ─── Colors ───────────────────────────────────────────────────────
G='\033[38;5;114m' B='\033[38;5;75m' Y='\033[38;5;221m'
R='\033[38;5;203m' D='\033[2m' N='\033[0m' W='\033[38;5;255m'

ok()   { echo -e "  ${G}✓${N} $1"; }
info() { echo -e "  ${B}→${N} $1"; }
warn() { echo -e "  ${Y}⚠${N} $1"; }
skip() { echo -e "  ${D}  skip: $1${N}"; }

echo ""
echo -e "  ${B}KOVO Backup${N}  ${D}v2${N}"
echo ""

# ─── Collect what exists ──────────────────────────────────────────
declare -A ITEMS

# Auth & Config (Tier 1 — always)
[ -f "$KOVO_DIR/config/.env" ]                    && ITEMS[config/.env]="auth"
[ -f "$KOVO_DIR/config/settings.yaml" ]           && ITEMS[config/settings.yaml]="auth"
[ -f "$KOVO_DIR/config/.env.template" ]           && ITEMS[config/.env.template]="auth"
[ -f "$KOVO_DIR/config/google-credentials.json" ] && ITEMS[config/google-credentials.json]="auth"
[ -f "$KOVO_DIR/config/google-token.json" ]       && ITEMS[config/google-token.json]="auth"

# Claude Code permissions
[ -f "$KOVO_DIR/.claude/settings.local.json" ]    && ITEMS[.claude/settings.local.json]="auth"

# Telegram caller session (Pyrogram)
for f in "$KOVO_DIR"/*.session "$KOVO_DIR"/config/*.session "$KOVO_DIR"/data/*.session; do
    [ -f "$f" ] && ITEMS[${f#$KOVO_DIR/}]="auth"
done

# Brain & Workspace (Tier 1 — always)
[ -d "$KOVO_DIR/workspace" ] && ITEMS[workspace/]="brain"

# Database
[ -f "$KOVO_DIR/data/kovo.db" ] && ITEMS[data/kovo.db]="brain"

# Security data
[ -d "$KOVO_DIR/data/security" ] && ITEMS[data/security/]="brain"

# Custom scripts
[ -d "$KOVO_DIR/scripts/experiments" ] && \
    [ "$(ls -A "$KOVO_DIR/scripts/experiments" 2>/dev/null)" ] && \
    ITEMS[scripts/experiments/]="brain"

# TOOLS.md (current tool registry — may have grown)
[ -f "$KOVO_DIR/workspace/TOOLS.md" ] && ITEMS[workspace/TOOLS.md]="brain"

# Package manifests (for reinstalling user-added packages)
ITEMS[_pip_freeze]="packages"
ITEMS[_apt_packages]="packages"
ITEMS[_npm_global]="packages"
ITEMS[_crontab]="packages"

# Media (Tier 2 — only with --full)
if $INCLUDE_MEDIA; then
    for d in photos documents images screenshots audio; do
        [ -d "$KOVO_DIR/data/$d" ] && \
            [ "$(ls -A "$KOVO_DIR/data/$d" 2>/dev/null)" ] && \
            ITEMS[data/$d/]="media"
    done
fi

# ─── List mode ────────────────────────────────────────────────────
if $LIST_ONLY; then
    echo -e "  ${W}Would backup:${N}"
    echo ""
    for category in auth brain packages media; do
        has_items=false
        for key in "${!ITEMS[@]}"; do
            [ "${ITEMS[$key]}" = "$category" ] && has_items=true && break
        done
        $has_items || continue

        case $category in
            auth)     echo -e "  ${Y}Authentication & Config${N}" ;;
            brain)    echo -e "  ${B}Brain & Memory${N}" ;;
            packages) echo -e "  ${G}Package Manifests${N}" ;;
            media)    echo -e "  ${R}Media Files${N}" ;;
        esac
        for key in $(echo "${!ITEMS[@]}" | tr ' ' '\n' | sort); do
            if [ "${ITEMS[$key]}" = "$category" ]; then
                if [[ "$key" == _* ]]; then
                    echo -e "    ${D}(generated)${N} ${key#_}"
                elif [[ "$key" == */ ]]; then
                    count=$(find "$KOVO_DIR/$key" -type f 2>/dev/null | wc -l)
                    size=$(du -sh "$KOVO_DIR/$key" 2>/dev/null | cut -f1)
                    echo -e "    $key  ${D}($count files, $size)${N}"
                else
                    size=$(du -sh "$KOVO_DIR/$key" 2>/dev/null | cut -f1)
                    echo -e "    $key  ${D}($size)${N}"
                fi
            fi
        done
        echo ""
    done
    if ! $INCLUDE_MEDIA; then
        echo -e "  ${D}Tip: use --full to include media files (photos, documents, audio)${N}"
    fi
    exit 0
fi

# ─── Build backup ─────────────────────────────────────────────────
mkdir -p "$STAGE" "$BACKUP_DIR"
info "Staging backup..."

# Copy auth & config
mkdir -p "$STAGE/config" "$STAGE/.claude"
for key in "${!ITEMS[@]}"; do
    [ "${ITEMS[$key]}" = "auth" ] || continue
    [[ "$key" == _* ]] && continue
    src="$KOVO_DIR/$key"
    dest="$STAGE/$key"
    mkdir -p "$(dirname "$dest")"
    cp -a "$src" "$dest" 2>/dev/null && ok "auth: $key" || skip "$key"
done

# Copy brain & workspace
for key in "${!ITEMS[@]}"; do
    [ "${ITEMS[$key]}" = "brain" ] || continue
    [[ "$key" == _* ]] && continue
    src="$KOVO_DIR/$key"
    dest="$STAGE/$key"
    mkdir -p "$(dirname "$dest")"
    if [[ "$key" == */ ]]; then
        cp -a "$src" "$dest" 2>/dev/null && ok "brain: $key" || skip "$key"
    else
        cp -a "$src" "$dest" 2>/dev/null && ok "brain: $key" || skip "$key"
    fi
done

# Generate package manifests
mkdir -p "$STAGE/packages"

# pip freeze — full and delta
if [ -f "$KOVO_DIR/venv/bin/pip" ]; then
    "$KOVO_DIR/venv/bin/pip" freeze 2>/dev/null > "$STAGE/packages/pip_freeze.txt"

    # Calculate delta from requirements.txt
    if [ -f "$KOVO_DIR/requirements.txt" ]; then
        # Get base package names from requirements.txt (lowercase, no version specifiers)
        base_pkgs=$(cat "$KOVO_DIR/requirements.txt" | grep -v '^#' | grep -v '^$' | \
            sed 's/[>=<!\[].*//; s/ //g' | tr '[:upper:]' '[:lower:]' | sort -u)

        # Get current packages, find ones not in base
        "$KOVO_DIR/venv/bin/pip" freeze 2>/dev/null | while IFS= read -r line; do
            pkg_name=$(echo "$line" | sed 's/==.*//' | tr '[:upper:]' '[:lower:]')
            if ! echo "$base_pkgs" | grep -qx "$pkg_name"; then
                echo "$line"
            fi
        done > "$STAGE/packages/pip_delta.txt"

        delta_count=$(wc -l < "$STAGE/packages/pip_delta.txt" | tr -d ' ')
        total_count=$(wc -l < "$STAGE/packages/pip_freeze.txt" | tr -d ' ')
        ok "packages: pip ($total_count total, $delta_count user-added)"
    else
        cp "$STAGE/packages/pip_freeze.txt" "$STAGE/packages/pip_delta.txt"
        ok "packages: pip (full freeze, no base to diff)"
    fi
else
    skip "pip (no venv found)"
fi

# apt packages
dpkg --get-selections 2>/dev/null | grep -v deinstall > "$STAGE/packages/apt_installed.txt"
ok "packages: apt ($(wc -l < "$STAGE/packages/apt_installed.txt" | tr -d ' ') packages)"

# npm global packages
if command -v npm &>/dev/null; then
    npm list -g --depth=0 2>/dev/null > "$STAGE/packages/npm_global.txt"
    ok "packages: npm global"
else
    skip "npm (not found)"
fi

# crontab
crontab -l 2>/dev/null > "$STAGE/packages/crontab.txt" || true
if [ -s "$STAGE/packages/crontab.txt" ]; then
    ok "packages: crontab ($(wc -l < "$STAGE/packages/crontab.txt" | tr -d ' ') entries)"
else
    skip "crontab (empty)"
fi

# Copy media if --full
if $INCLUDE_MEDIA; then
    for key in "${!ITEMS[@]}"; do
        [ "${ITEMS[$key]}" = "media" ] || continue
        src="$KOVO_DIR/$key"
        dest="$STAGE/$key"
        mkdir -p "$(dirname "$dest")"
        cp -a "$src" "$dest" 2>/dev/null
        count=$(find "$KOVO_DIR/$key" -type f 2>/dev/null | wc -l)
        size=$(du -sh "$KOVO_DIR/$key" 2>/dev/null | cut -f1)
        ok "media: $key ($count files, $size)"
    done
fi

# ─── Generate manifest.json ──────────────────────────────────────
info "Building manifest..."

KOVO_VER=$(grep -oP 'KOVO_VERSION="\K[^"]+' "$KOVO_DIR/bootstrap.sh" 2>/dev/null || echo "unknown")
HOSTNAME=$(hostname 2>/dev/null || echo "unknown")
PY_VER=$(python3 --version 2>/dev/null | cut -d' ' -f2 || echo "unknown")
NODE_VER=$(node --version 2>/dev/null || echo "unknown")

# Count things
MEMORY_DAYS=$(find "$KOVO_DIR/workspace/memory" -name "*.md" -not -name "archive" 2>/dev/null | wc -l | tr -d ' ')
SKILLS_COUNT=$(find "$KOVO_DIR/workspace/skills" -name "SKILL.md" 2>/dev/null | wc -l | tr -d ' ')
DB_SIZE=$(du -sm "$KOVO_DIR/data/kovo.db" 2>/dev/null | cut -f1 || echo "0")
STAGE_SIZE=$(du -sm "$STAGE" 2>/dev/null | cut -f1 || echo "0")

# Check auth status
has_file() { [ -f "$1" ] && echo "true" || echo "false"; }
TBOT=$(grep -q "TELEGRAM_BOT_TOKEN=." "$KOVO_DIR/config/.env" 2>/dev/null && echo "true" || echo "false")
TCALLER=$(ls "$KOVO_DIR"/*.session "$KOVO_DIR"/config/*.session "$KOVO_DIR"/data/*.session 2>/dev/null | head -1 && echo "true" || echo "false")
GOAUTH=$(has_file "$KOVO_DIR/config/google-token.json")
GROQ=$(grep -q "GROQ_API_KEY=." "$KOVO_DIR/config/.env" 2>/dev/null && echo "true" || echo "false")
GHUB=$(grep -q "GITHUB_TOKEN=." "$KOVO_DIR/config/.env" 2>/dev/null && echo "true" || echo "false")

# Tier info
TIERS="[\"core\""
$INCLUDE_MEDIA && TIERS+=", \"media\""
TIERS+="]"

cat > "$STAGE/manifest.json" << MANIFEST_EOF
{
  "kovo_version": "$KOVO_VER",
  "backup_version": "2.0",
  "backup_date": "$(date -Iseconds)",
  "hostname": "$HOSTNAME",
  "tiers": $TIERS,
  "stats": {
    "memory_days": $MEMORY_DAYS,
    "skills_count": $SKILLS_COUNT,
    "db_size_mb": $DB_SIZE,
    "pip_delta_count": $(wc -l < "$STAGE/packages/pip_delta.txt" 2>/dev/null | tr -d ' ' || echo 0),
    "total_size_mb": $STAGE_SIZE
  },
  "auth_status": {
    "telegram_bot": $TBOT,
    "telegram_caller": $(ls "$KOVO_DIR"/*.session "$KOVO_DIR"/config/*.session "$KOVO_DIR"/data/*.session 2>/dev/null | head -1 > /dev/null && echo "true" || echo "false"),
    "google_oauth": $GOAUTH,
    "claude_code": "requires_reauth",
    "groq": $GROQ,
    "github": $GHUB
  },
  "system": {
    "python_version": "$PY_VER",
    "node_version": "$NODE_VER",
    "platform": "$(uname -s) $(uname -r)"
  }
}
MANIFEST_EOF
ok "manifest.json"

# ─── Create archive ──────────────────────────────────────────────
SUFFIX="core"
$INCLUDE_MEDIA && SUFFIX="full"
ARCHIVE="kovo-backup-${SUFFIX}_${DATE}.tar.gz"

info "Compressing → $ARCHIVE"
tar czf "$BACKUP_DIR/$ARCHIVE" -C "$STAGE" .
rm -rf "$STAGE"

FINAL_SIZE=$(du -sh "$BACKUP_DIR/$ARCHIVE" | cut -f1)
ok "Backup complete: $FINAL_SIZE"

# ─── Cleanup old backups ─────────────────────────────────────────
OLD=$(find "$BACKUP_DIR" -name "kovo-backup-*.tar.gz" -mtime +$RETENTION_DAYS 2>/dev/null | wc -l | tr -d ' ')
find "$BACKUP_DIR" -name "kovo-backup-*.tar.gz" -mtime +$RETENTION_DAYS -delete 2>/dev/null
[ "$OLD" -gt 0 ] && info "Cleaned $OLD backup(s) older than ${RETENTION_DAYS} days"

# ─── Summary ──────────────────────────────────────────────────────
echo ""
echo -e "  ${W}╔═══════════════════════════════════════════════╗${N}"
echo -e "  ${W}║  Backup: ${G}$ARCHIVE${W}${N}"
echo -e "  ${W}║  Size:   ${G}$FINAL_SIZE${W}${N}"
echo -e "  ${W}║  Path:   ${D}$BACKUP_DIR/$ARCHIVE${W}${N}"
echo -e "  ${W}╚═══════════════════════════════════════════════╝${N}"
echo ""
echo -e "  ${D}Contains:${N}"
echo -e "  ${D}  • Config + credentials + OAuth tokens${N}"
echo -e "  ${D}  • Claude Code permissions${N}"
echo -e "  ${D}  • Telegram caller session${N}"
echo -e "  ${D}  • Workspace (${MEMORY_DAYS} days memory, ${SKILLS_COUNT} skills)${N}"
echo -e "  ${D}  • SQLite database (${DB_SIZE}MB)${N}"
echo -e "  ${D}  • Package manifests (pip delta, apt, npm, crontab)${N}"
$INCLUDE_MEDIA && echo -e "  ${D}  • Media files (photos, documents, audio, images)${N}"
echo ""
echo -e "  ${D}Restore on new machine:${N}"
echo -e "  ${D}  1. Run bootstrap.sh${N}"
echo -e "  ${D}  2. Open Setup Wizard → Restore from Backup${N}"
echo -e "  ${D}  3. Upload this file${N}"
echo -e "  ${D}  4. Only re-run: claude login${N}"
echo ""
