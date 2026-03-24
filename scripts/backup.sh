#!/bin/bash
WORKSPACE="/opt/miniclaw/workspace"
BACKUP_DIR="/opt/miniclaw/data/backups"
DATE=$(date +%Y%m%d)
mkdir -p "$BACKUP_DIR"
tar czf "$BACKUP_DIR/workspace_$DATE.tar.gz" -C /opt/miniclaw workspace/
find "$BACKUP_DIR" -name "workspace_*.tar.gz" -mtime +30 -delete
echo "Backup: $BACKUP_DIR/workspace_$DATE.tar.gz"
