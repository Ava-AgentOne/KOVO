#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# KOVO Update Script — Safe self-updater
#
# Only triggers on VERSION changes (releases), not every commit.
#
# Usage:
#   bash /opt/kovo/scripts/update.sh --check     # Check only
#   bash /opt/kovo/scripts/update.sh --apply      # Apply update
#   bash /opt/kovo/scripts/update.sh --json       # Check (JSON for API)
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

get_local_version() {
    grep -m1 'KOVO_VERSION=' bootstrap.sh 2>/dev/null | sed 's/.*="\(.*\)"/\1/' || echo "0.0"
}

get_remote_version() {
    curl -sf --max-time 10 "$REPO_URL/bootstrap.sh" 2>/dev/null | \
        grep -m1 'KOVO_VERSION=' | sed 's/.*="\(.*\)"/\1/' || echo ""
}

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
    }))
except: print('{}')
" 2>/dev/null || echo "{}"
}

get_local_sha() {
    git rev-parse --short HEAD 2>/dev/null || echo "unknown"
}

version_gt() {
    [ "$(printf '%s\n' "$1" "$2" | sort -V | head -n1)" != "$1" ]
}

# ── CHECK ──────────────────────────────────────────────────────
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
        echo "  Latest release: v$REMOTE_VER"
        if $UPDATE_AVAILABLE; then
            echo ""
            echo "  ✓ New release available!"
            echo "  Run: bash /opt/kovo/scripts/update.sh --apply"
        else
            echo "  · You're on the latest release."
        fi
        echo ""
    fi
    exit 0
fi

# ── APPLY ──────────────────────────────────────────────────────
if [ "$MODE" = "apply" ]; then
    LOCAL_VER=$(get_local_version)
    REMOTE_VER=$(get_remote_version)

    log "Starting update: v$LOCAL_VER → v$REMOTE_VER"

    log "Step 1: Pre-flight..."
    [ -d "$KOVO_DIR/.git" ] || { log "ERROR: Not a git repo"; exit 1; }

    log "Step 2: Pre-update backup..."
    BACKUP_DIR="$KOVO_DIR/data/backups"
    mkdir -p "$BACKUP_DIR"
    BACKUP_NAME="pre-update_${LOCAL_VER}_$(date +%Y%m%d_%H%M%S).tar.gz"
    tar czf "$BACKUP_DIR/$BACKUP_NAME" -C "$KOVO_DIR" \
        workspace/ config/settings.yaml config/.env \
        --ignore-failed-read 2>/dev/null || true
    log "  Backup: $BACKUP_NAME"

    log "Step 3: Stashing local changes..."
    STASH_NEEDED=false
    if ! git diff --quiet 2>/dev/null || ! git diff --cached --quiet 2>/dev/null; then
        git stash push -m "pre-update-$(date +%Y%m%d_%H%M%S)" 2>/dev/null || true
        STASH_NEEDED=true
        log "  Stashed"
    else
        log "  Clean"
    fi

    log "Step 4: Pulling latest..."
    git fetch origin main 2>&1 | tail -2 | while read line; do log "  $line"; done

    CHANGED_FILES=$(git diff --name-only HEAD origin/main 2>/dev/null || echo "")
    REQUIREMENTS_CHANGED=false
    FRONTEND_CHANGED=false
    echo "$CHANGED_FILES" | grep -q "requirements.txt" && REQUIREMENTS_CHANGED=true
    echo "$CHANGED_FILES" | grep -q "src/dashboard/frontend/" && FRONTEND_CHANGED=true

    git merge origin/main --no-edit 2>&1 | while read line; do log "  $line"; done
    NEW_VER=$(get_local_version)
    log "  Now at v$NEW_VER ($(get_local_sha))"

    if $STASH_NEEDED; then
        log "Step 5: Restoring stash..."
        git stash pop 2>/dev/null && log "  Applied" || log "  ⚠ Conflict — check git stash"
    fi

    if $REQUIREMENTS_CHANGED; then
        log "Step 6: Installing new dependencies..."
        "$KOVO_DIR/venv/bin/pip" install -r "$KOVO_DIR/requirements.txt" -q 2>&1 | tail -3
    fi

    if $FRONTEND_CHANGED; then
        log "Step 7: Rebuilding dashboard..."
        cd "$KOVO_DIR/src/dashboard/frontend"
        npm install --silent 2>&1 | tail -1
        npm run build 2>&1 | tail -3
        cd "$KOVO_DIR"
    fi

    log "Step 8: Checking new templates..."
    for tmpl in workspace/*.md.template; do
        [ -f "$tmpl" ] || continue
        live="${tmpl%.template}"
        [ ! -f "$live" ] && cp "$tmpl" "$live" && log "  New: $(basename "$live")"
    done

    log "Step 9: Restarting service..."
    sudo systemctl restart kovo 2>/dev/null && log "  Service restarted" || log "  ⚠ Restart failed"

    log ""
    log "✓ Update complete: v$LOCAL_VER → v$NEW_VER"
    log ""
    exit 0
fi
