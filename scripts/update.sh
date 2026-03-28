#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# KOVO Update Script — Safe self-updater
#
# Usage:
#   bash /opt/kovo/scripts/update.sh --check     # Check only
#   bash /opt/kovo/scripts/update.sh --apply      # Apply update
#   bash /opt/kovo/scripts/update.sh --json       # Check (JSON output for API)
# ═══════════════════════════════════════════════════════════════════

set -euo pipefail

KOVO_DIR="/opt/kovo"
LOG_FILE="/opt/kovo/logs/update.log"
REPO_URL="https://raw.githubusercontent.com/Ava-AgentOne/kovo/main"
GITHUB_API="https://api.github.com/repos/Ava-AgentOne/kovo"

cd "$KOVO_DIR" || exit 1

MODE="check"
JSON=false
for arg in "$@"; do
    case "$arg" in
        --check) MODE="check" ;;
        --apply) MODE="apply" ;;
        --json)  MODE="check"; JSON=true ;;
    esac
done

log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo "$msg" >> "$LOG_FILE"
    $JSON || echo "$msg"
}

# ── Get current version ────────────────────────────────────────
get_local_version() {
    grep -m1 'KOVO_VERSION=' bootstrap.sh 2>/dev/null | sed 's/.*="\(.*\)"/\1/' || echo "0.0.0"
}

# ── Get latest version from GitHub ─────────────────────────────
get_remote_version() {
    curl -sf --max-time 10 "$REPO_URL/bootstrap.sh" 2>/dev/null | \
        grep -m1 'KOVO_VERSION=' | sed 's/.*="\(.*\)"/\1/' || echo ""
}

# ── Get latest commit info ─────────────────────────────────────
get_latest_commit() {
    curl -sf --max-time 10 "$GITHUB_API/commits/main" 2>/dev/null | \
        python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(json.dumps({
        'sha': d['sha'][:7],
        'message': d['commit']['message'].split('\n')[0],
        'date': d['commit']['committer']['date'],
        'author': d['commit']['committer']['name'],
    }))
except: print('{}')
" 2>/dev/null || echo "{}"
}

# ── Get local commit SHA ───────────────────────────────────────
get_local_sha() {
    git rev-parse --short HEAD 2>/dev/null || echo "unknown"
}

# ── Version comparison ─────────────────────────────────────────
version_gt() {
    # Returns 0 if $1 > $2
    [ "$(printf '%s\n' "$1" "$2" | sort -V | head -n1)" != "$1" ]
}

# ── CHECK MODE ─────────────────────────────────────────────────
if [ "$MODE" = "check" ]; then
    LOCAL_VER=$(get_local_version)
    REMOTE_VER=$(get_remote_version)
    LOCAL_SHA=$(get_local_sha)
    COMMIT_INFO=$(get_latest_commit)

    if [ -z "$REMOTE_VER" ]; then
        if $JSON; then
            echo '{"update_available":false,"error":"Could not reach GitHub","local_version":"'"$LOCAL_VER"'","local_sha":"'"$LOCAL_SHA"'"}'
        else
            echo "Could not reach GitHub to check for updates."
        fi
        exit 1
    fi

    UPDATE_AVAILABLE=false
    if version_gt "$REMOTE_VER" "$LOCAL_VER"; then
        UPDATE_AVAILABLE=true
    fi

    # Also check if commits differ even if version is same
    REMOTE_SHA=$(echo "$COMMIT_INFO" | python3 -c "import sys,json; print(json.load(sys.stdin).get('sha',''))" 2>/dev/null || echo "")
    if [ "$LOCAL_SHA" != "$REMOTE_SHA" ] && [ -n "$REMOTE_SHA" ]; then
        UPDATE_AVAILABLE=true
    fi

    if $JSON; then
        cat << JSONEOF
{
    "update_available": $UPDATE_AVAILABLE,
    "local_version": "$LOCAL_VER",
    "remote_version": "$REMOTE_VER",
    "local_sha": "$LOCAL_SHA",
    "latest_commit": $COMMIT_INFO
}
JSONEOF
    else
        echo ""
        echo "  Current: v$LOCAL_VER ($LOCAL_SHA)"
        echo "  Latest:  v$REMOTE_VER"
        if $UPDATE_AVAILABLE; then
            echo ""
            echo "  ✓ Update available!"
            echo "  Run: bash /opt/kovo/scripts/update.sh --apply"
        else
            echo ""
            echo "  · You're up to date."
        fi
        echo ""
    fi
    exit 0
fi

# ── APPLY MODE ─────────────────────────────────────────────────
if [ "$MODE" = "apply" ]; then
    LOCAL_VER=$(get_local_version)
    REMOTE_VER=$(get_remote_version)

    log "Starting update: v$LOCAL_VER → v$REMOTE_VER"

    # Step 1: Pre-flight checks
    log "Step 1: Pre-flight checks..."
    if [ ! -d "$KOVO_DIR/.git" ]; then
        log "ERROR: Not a git repository. Cannot update."
        exit 1
    fi

    # Step 2: Backup before update
    log "Step 2: Creating pre-update backup..."
    BACKUP_DIR="$KOVO_DIR/data/backups"
    mkdir -p "$BACKUP_DIR"
    BACKUP_NAME="pre-update_${LOCAL_VER}_$(date +%Y%m%d_%H%M%S).tar.gz"
    tar czf "$BACKUP_DIR/$BACKUP_NAME" \
        -C "$KOVO_DIR" \
        workspace/ config/settings.yaml config/.env \
        --ignore-failed-read 2>/dev/null || true
    log "  Backup: $BACKUP_NAME"

    # Step 3: Stash any local changes to tracked files
    log "Step 3: Stashing local changes..."
    STASH_NEEDED=false
    if ! git diff --quiet 2>/dev/null || ! git diff --cached --quiet 2>/dev/null; then
        git stash push -m "pre-update-$(date +%Y%m%d_%H%M%S)" 2>/dev/null || true
        STASH_NEEDED=true
        log "  Local changes stashed"
    else
        log "  No local changes to stash"
    fi

    # Step 4: Pull latest code
    log "Step 4: Pulling latest code..."
    git fetch origin main 2>&1 | tail -2 | while read line; do log "  $line"; done

    # Check what changed before merging
    CHANGED_FILES=$(git diff --name-only HEAD origin/main 2>/dev/null || echo "")
    REQUIREMENTS_CHANGED=false
    FRONTEND_CHANGED=false

    echo "$CHANGED_FILES" | grep -q "requirements.txt" && REQUIREMENTS_CHANGED=true
    echo "$CHANGED_FILES" | grep -q "src/dashboard/frontend/" && FRONTEND_CHANGED=true

    git merge origin/main --no-edit 2>&1 | while read line; do log "  $line"; done
    NEW_VER=$(get_local_version)
    log "  Updated to v$NEW_VER ($(get_local_sha))"

    # Step 5: Restore stashed changes
    if $STASH_NEEDED; then
        log "Step 5: Restoring local changes..."
        if git stash pop 2>/dev/null; then
            log "  Stash applied cleanly"
        else
            log "  ⚠ Stash conflict — your local changes are in git stash"
            log "  Run 'cd /opt/kovo && git stash show' to review"
        fi
    else
        log "Step 5: No stash to restore (skipped)"
    fi

    # Step 6: Install new dependencies
    if $REQUIREMENTS_CHANGED; then
        log "Step 6: Installing new Python dependencies..."
        "$KOVO_DIR/venv/bin/pip" install -r "$KOVO_DIR/requirements.txt" -q 2>&1 | tail -3 | while read line; do log "  $line"; done
        log "  Dependencies updated"
    else
        log "Step 6: No new Python dependencies (skipped)"
    fi

    # Step 7: Rebuild dashboard
    if $FRONTEND_CHANGED; then
        log "Step 7: Rebuilding dashboard..."
        cd "$KOVO_DIR/src/dashboard/frontend"
        npm install --silent 2>&1 | tail -1
        npm run build 2>&1 | tail -3 | while read line; do log "  $line"; done
        cd "$KOVO_DIR"
        log "  Dashboard rebuilt"
    else
        log "Step 7: No frontend changes (skipped)"
    fi

    # Step 8: Copy new templates (don't overwrite live files)
    log "Step 8: Checking for new workspace templates..."
    for tmpl in workspace/*.md.template; do
        [ -f "$tmpl" ] || continue
        live="${tmpl%.template}"
        if [ ! -f "$live" ]; then
            cp "$tmpl" "$live"
            log "  New template → live: $(basename "$live")"
        fi
    done

    # Step 9: Restart service
    log "Step 9: Restarting KOVO service..."
    sudo systemctl restart kovo 2>/dev/null && log "  Service restarted" || log "  ⚠ Service restart failed"

    log ""
    log "═══════════════════════════════════════════════════════"
    log " ✓ Update complete: v$LOCAL_VER → v$NEW_VER"
    log "═══════════════════════════════════════════════════════"
    log ""
    log " Changed files:"
    echo "$CHANGED_FILES" | head -20 | while read f; do [ -n "$f" ] && log "   • $f"; done
    log ""
    log " Pre-update backup: $BACKUP_NAME"
    [ "$REQUIREMENTS_CHANGED" = true ] && log " Python dependencies: updated"
    [ "$FRONTEND_CHANGED" = true ] && log " Dashboard: rebuilt"
    log ""

    exit 0
fi
