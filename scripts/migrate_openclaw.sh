#!/bin/bash
# Migrate OpenClaw workspace to KOVO
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
    echo -e "\n## KOVO Migration Notes\n- Migrated from OpenClaw on $(date)\n- Update paths and hosts for VM" >> "$TARGET/TOOLS.md"
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
