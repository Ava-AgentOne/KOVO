#!/bin/bash
# backup.sh — KOVO workspace + config + database backup
# Usage: bash /opt/kovo/scripts/backup.sh
set -e

KOVO_DIR="/opt/kovo"
BACKUP_DIR="$KOVO_DIR/data/backups"
DATE=$(date +%Y%m%d_%H%M)
mkdir -p "$BACKUP_DIR"

# Workspace (SOUL.md, MEMORY.md, skills, memory logs, etc.)
tar czf "$BACKUP_DIR/workspace_$DATE.tar.gz" -C "$KOVO_DIR" workspace/ 2>/dev/null

# Config (.env, settings.yaml, credentials — excludes venv and node_modules)
tar czf "$BACKUP_DIR/config_$DATE.tar.gz" -C "$KOVO_DIR" config/ .claude/ 2>/dev/null || true

# Database
if [ -f "$KOVO_DIR/data/kovo.db" ]; then
    cp "$KOVO_DIR/data/kovo.db" "$BACKUP_DIR/kovo_db_$DATE.sqlite"
fi

# Security baseline
if [ -f "$KOVO_DIR/data/security/baseline.json" ]; then
    cp "$KOVO_DIR/data/security/baseline.json" "$BACKUP_DIR/security_baseline_$DATE.json"
fi

# Cleanup: remove backups older than retention period (default 30 days)
RETENTION_DAYS="${1:-30}"
find "$BACKUP_DIR" -name "workspace_*.tar.gz" -mtime +"$RETENTION_DAYS" -delete 2>/dev/null
find "$BACKUP_DIR" -name "config_*.tar.gz" -mtime +"$RETENTION_DAYS" -delete 2>/dev/null
find "$BACKUP_DIR" -name "kovo_db_*.sqlite" -mtime +"$RETENTION_DAYS" -delete 2>/dev/null
find "$BACKUP_DIR" -name "security_baseline_*.json" -mtime +"$RETENTION_DAYS" -delete 2>/dev/null

# Report
TOTAL=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1)
COUNT=$(ls -1 "$BACKUP_DIR" 2>/dev/null | wc -l)
echo "✓ Backup complete: workspace + config + db ($DATE)"
echo "  Location: $BACKUP_DIR"
echo "  Total: $TOTAL across $COUNT files"
echo "  Retention: $RETENTION_DAYS days"
