"""
Safe shell command execution for agent use.

Commands are classified as:
  safe      — execute immediately
  dangerous — blocked; returned as error with explanation

All executions are logged.
"""
from __future__ import annotations

import logging
import re
import subprocess

log = logging.getLogger(__name__)

# Prefixes/patterns that are always safe (read-only / harmless)
_SAFE_PATTERNS = re.compile(
    r"^("
    r"df |du |free|top |ps |ls |cat |head |tail |wc |grep |find |locate |which |whereis |"
    r"echo |printf |pwd |env |printenv |uname |hostname |uptime |date |cal |whoami |id |"
    r"ip |ifconfig |netstat |ss |ping |traceroute |nslookup |dig |curl |wget |"
    r"lsblk |lscpu |lshw |lspci |lsusb |dmidecode |"
    r"docker ps|docker images|docker logs|docker stats|docker inspect|"
    r"systemctl status|systemctl is-active|systemctl list-units|"
    r"journalctl |dmesg |last |lastlog |who |w |"
    r"git status|git log|git diff|git show|git branch|git remote|"
    r"python3? |pip |/opt/kovo/venv/bin/|"
    r"cat /proc/|cat /sys/|"
    r"less |more |file |stat |readlink |realpath |"
    r"tar |zip |unzip |gzip |gunzip |"
    r"sort |uniq |cut |awk |sed |tr |"
    r"mkdir |touch |cp |mv |ln "
    r")",
    re.IGNORECASE,
)

# ── Public command lists (checked before regex patterns) ──────────────────────

BLOCKED_COMMANDS: list[str] = [
    "rm -rf",
    "rm -fr",
    "mkfs",
    "dd if=",
    "shutdown",
    "poweroff",
    "halt",
    "reboot",
    "fdisk",
    "parted",
    "gdisk",
    "iptables -F",
    "ufw disable",
    "DROP TABLE",
    "DELETE FROM",
    "chmod 777",
    "chown root",
    "wget | bash",
    "curl | bash",
    "curl | sh",
]

CONFIRM_COMMANDS: list[str] = [
    "systemctl stop",
    "systemctl disable",
    "systemctl mask",
    "systemctl kill",
    "kill -9",
    "pkill -9",
    "git push",
    "git reset --hard",
    "pip uninstall",
    "apt remove",
    "apt purge",
    "docker rm",
    "docker rmi",
    "docker stop",
]


def is_blocked(command: str) -> bool:
    """Return True if the command matches a BLOCKED_COMMANDS entry."""
    cmd_lower = command.lower()
    return any(b.lower() in cmd_lower for b in BLOCKED_COMMANDS)


def needs_confirmation(command: str) -> bool:
    """Return True if the command matches a CONFIRM_COMMANDS entry."""
    cmd_lower = command.lower()
    return any(c.lower() in cmd_lower for c in CONFIRM_COMMANDS)


# Patterns that are always dangerous — blocked
_DANGEROUS_PATTERNS = re.compile(
    r"(rm\s+-rf|rm\s+-fr|"
    r":.*>\s*/dev/null.*>&|"
    r">\s*/dev/sd|>\s*/dev/nvme|>\s*/dev/xvd|"
    r"dd\s+if=|mkfs\.|"
    r"fdisk|parted|gdisk|"
    r"shutdown|poweroff|halt|reboot|"
    r"systemctl\s+(stop|disable|mask|kill)\s|"
    r"kill\s+-9|pkill\s+-9|"
    r"chmod\s+777|chown\s+root|"
    r"iptables\s+-F|ufw\s+disable|"
    r"DROP\s+TABLE|DELETE\s+FROM|"
    r"wget.*\|\s*bash|curl.*\|\s*bash|curl.*\|\s*sh|"
    r"eval\s+\$|exec\s+\$"
    r")",
    re.IGNORECASE,
)


def classify(command: str) -> str:
    """Returns 'safe', 'caution', or 'dangerous'."""
    cmd = command.strip()
    if is_blocked(cmd) or _DANGEROUS_PATTERNS.search(cmd):
        return "dangerous"
    if needs_confirmation(cmd):
        return "caution"
    if _SAFE_PATTERNS.match(cmd):
        return "safe"
    return "caution"  # unknown — allowed but logged prominently


def run(
    command: str,
    timeout: int = 30,
    cwd: str = "/opt/kovo",
    allow_caution: bool = True,
) -> dict:
    """
    Execute a shell command.
    Returns: {ok, stdout, stderr, exit_code, command, classification}
    """
    safety = classify(command)

    if safety == "dangerous":
        log.warning("BLOCKED dangerous command: %s", command)
        return {
            "ok": False,
            "stdout": "",
            "stderr": f"Command blocked: '{command}' matches a dangerous pattern. "
                      f"Run this manually after reviewing it.",
            "exit_code": -1,
            "command": command,
            "classification": "dangerous",
        }

    if safety == "caution" and not allow_caution:
        log.warning("BLOCKED caution command (allow_caution=False): %s", command)
        return {
            "ok": False,
            "stdout": "",
            "stderr": f"Command '{command}' requires explicit approval.",
            "exit_code": -1,
            "command": command,
            "classification": "caution",
        }

    if safety == "caution":
        log.warning("Executing CAUTION command: %s", command)
    else:
        log.info("Executing: %s", command)

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
        return {
            "ok": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
            "command": command,
            "classification": safety,
        }
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "stdout": "",
            "stderr": f"Command timed out after {timeout}s",
            "exit_code": -1,
            "command": command,
            "classification": safety,
        }
    except Exception as e:
        return {
            "ok": False,
            "stdout": "",
            "stderr": str(e),
            "exit_code": -1,
            "command": command,
            "classification": safety,
        }


def format_result(result: dict, max_output: int = 2000) -> str:
    """Format a shell result dict for display."""
    lines = [f"```\n$ {result['command']}"]
    if result["stdout"]:
        out = result["stdout"][:max_output]
        if len(result["stdout"]) > max_output:
            out += f"\n… ({len(result['stdout']) - max_output} chars truncated)"
        lines.append(out)
    if result["stderr"] and not result["ok"]:
        lines.append(f"STDERR: {result['stderr'][:500]}")
    if not result["ok"] and result["exit_code"] != 0:
        lines.append(f"Exit code: {result['exit_code']}")
    lines.append("```")
    return "\n".join(lines)
