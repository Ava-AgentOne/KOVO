#!/bin/bash
# Security audit runner — called by dashboard API
# Collects system state, compares to baseline, saves results

SEC_DIR="/opt/kovo/data/security"
mkdir -p "$SEC_DIR"

TIMESTAMP=$(date -Iseconds)
FINDINGS=()
STATUS="clean"

# --- Network: open ports ---
PORTS=$(ss -tlnp 2>/dev/null | grep LISTEN | awk '{print $4}' | sed 's/.*://' | sort -n | uniq | tr '\n' ',' | sed 's/,$//')

# --- Packages: count ---
PKG_COUNT=$(dpkg --get-selections 2>/dev/null | grep -v deinstall | wc -l)

# --- Users with shell ---
USERS=$(grep -v 'nologin\|false\|sync\|halt\|shutdown' /etc/passwd | cut -d: -f1 | tr '\n' ',' | sed 's/,$//')

# --- SSH config ---
SSH_ROOT=$(grep -i "^PermitRootLogin" /etc/ssh/sshd_config 2>/dev/null | awk '{print $2}' || echo "unknown")
SSH_PASSWD=$(grep -i "^PasswordAuthentication" /etc/ssh/sshd_config 2>/dev/null | awk '{print $2}' || echo "unknown")

# --- Failed logins (last 7 days) ---
FAILED_LOGINS=$(grep "Failed password" /var/log/auth.log 2>/dev/null | wc -l || echo "0")

# --- Security updates ---
SEC_UPDATES=$(apt list --upgradable 2>/dev/null | grep -c "security" || echo "0")

# --- SUID binaries ---
SUID_COUNT=$(find / -type f \( -perm -4000 -o -perm -2000 \) 2>/dev/null | wc -l)

# --- ClamAV scan (quick, /tmp and /dev/shm only) ---
MALWARE="not_installed"
if command -v clamscan &>/dev/null; then
    CLAM_OUT=$(clamscan -r /tmp /dev/shm --no-summary 2>/dev/null)
    if echo "$CLAM_OUT" | grep -q "FOUND"; then
        MALWARE="found"
        STATUS="critical"
        FINDINGS+=("Malware detected by ClamAV")
    else
        MALWARE="clean"
    fi
fi

# --- chkrootkit ---
ROOTKIT="not_installed"
if command -v chkrootkit &>/dev/null; then
    CHKROOT=$(sudo chkrootkit 2>/dev/null | grep "INFECTED" | head -5)
    if [ -n "$CHKROOT" ]; then
        ROOTKIT="infected"
        STATUS="critical"
        FINDINGS+=("Rootkit detected by chkrootkit")
    else
        ROOTKIT="clean"
    fi
fi

# --- Check for suspicious files in /tmp ---
SUSP_TMP=$(find /tmp /dev/shm -type f -executable 2>/dev/null | head -5)
if [ -n "$SUSP_TMP" ]; then
    STATUS="warning"
    FINDINGS+=("Executable files found in /tmp or /dev/shm")
fi

# --- Failed logins threshold ---
if [ "$FAILED_LOGINS" -gt 20 ]; then
    STATUS="warning"
    FINDINGS+=("$FAILED_LOGINS failed login attempts detected")
fi

# --- Security updates threshold ---
if [ "$SEC_UPDATES" -gt 5 ]; then
    if [ "$STATUS" = "clean" ]; then STATUS="warning"; fi
    FINDINGS+=("$SEC_UPDATES security updates available")
fi

# --- Build findings JSON array ---
FINDINGS_JSON="["
for i in "${!FINDINGS[@]}"; do
    if [ $i -gt 0 ]; then FINDINGS_JSON+=","; fi
    FINDINGS_JSON+="\"${FINDINGS[$i]}\""
done
FINDINGS_JSON+="]"

# --- Build summary ---
if [ "$STATUS" = "clean" ]; then
    SUMMARY="All clear — $PKG_COUNT packages, $SUID_COUNT SUID binaries, $FAILED_LOGINS failed logins"
elif [ "$STATUS" = "warning" ]; then
    SUMMARY="${#FINDINGS[@]} issue(s) found"
else
    SUMMARY="CRITICAL — ${#FINDINGS[@]} issue(s) require immediate attention"
fi

# --- Write latest.json ---
cat > "$SEC_DIR/latest.json" << JSONEOF
{
  "status": "$STATUS",
  "timestamp": "$TIMESTAMP",
  "summary": "$SUMMARY",
  "findings": $FINDINGS_JSON,
  "details": {
    "ports": "$PORTS",
    "packages": $PKG_COUNT,
    "users": "$USERS",
    "ssh_root_login": "$SSH_ROOT",
    "ssh_password_auth": "$SSH_PASSWD",
    "failed_logins": $FAILED_LOGINS,
    "security_updates": $SEC_UPDATES,
    "suid_binaries": $SUID_COUNT,
    "malware": "$MALWARE",
    "rootkit": "$ROOTKIT"
  }
}
JSONEOF

# --- Append to history ---
HIST_FILE="$SEC_DIR/history.json"
if [ ! -f "$HIST_FILE" ]; then
    echo '{"history":[]}' > "$HIST_FILE"
fi

# Use python to prepend to history (safer JSON handling)
python3 -c "
import json, sys
entry = {'status': '$STATUS', 'timestamp': '$TIMESTAMP', 'summary': '$SUMMARY', 'findings_count': ${#FINDINGS[@]}}
try:
    hist = json.load(open('$HIST_FILE'))
except:
    hist = {'history': []}
hist['history'].insert(0, entry)
hist['history'] = hist['history'][:50]
json.dump(hist, open('$HIST_FILE', 'w'), indent=2)
"

echo "Security audit complete: $STATUS"
