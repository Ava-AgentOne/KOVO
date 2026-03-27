"""
Telegram formatting helpers — emoji, Unicode progress bars, inline keyboards,
and the persistent reply keyboard for all Kovo command responses.

Design rules:
- 30-35 characters per line max (mobile Telegram width)
- Progress bars: ▓ (filled) / ░ (empty), default 10 chars
- Aligned columns wrapped in triple-backtick for monospace rendering
- All formatters are sync and safe to run in a thread executor
"""
from __future__ import annotations

import re
import time
from datetime import date

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

# ── Persistent reply keyboard ─────────────────────────────────────────────────
# Emoji-label buttons (no slash) so the keyboard looks clean.
# A MessageHandler in bot.py intercepts these texts and calls the right handler.

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        [KeyboardButton("📡 Status"), KeyboardButton("🖥 Health")],
        [KeyboardButton("🧠 Memory"), KeyboardButton("💾 Storage")],
        [KeyboardButton("📚 Skills"), KeyboardButton("🔧 Tools")],
    ],
    resize_keyboard=True,
    is_persistent=True,
)

# Map keyboard button text → command string (used by bot.py router)
BUTTON_TO_COMMAND: dict[str, str] = {
    "📡 Status":  "/status",
    "🖥 Health":  "/health",
    "🧠 Memory":  "/memory",
    "💾 Storage": "/storage",
    "📚 Skills":  "/skills",
    "🔧 Tools":   "/tools",
}

# ── Inline keyboard factories ─────────────────────────────────────────────────

def perm_inline() -> InlineKeyboardMarkup:
    """Approve / Deny buttons for sandbox permission requests."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Approve", callback_data="perm_approve"),
        InlineKeyboardButton("❌ Deny",    callback_data="perm_deny"),
    ]])


def purge_inline() -> InlineKeyboardMarkup:
    """Confirm / Cancel buttons for /purge operations."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🗑 Yes, delete", callback_data="purge_confirm"),
        InlineKeyboardButton("Cancel",         callback_data="purge_cancel"),
    ]])


def agent_inline() -> InlineKeyboardMarkup:
    """Create / Skip buttons for sub-agent creation suggestions."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("👍 Create it", callback_data="agent_approve"),
        InlineKeyboardButton("Not now",      callback_data="agent_deny"),
    ]])


# ── Utilities ─────────────────────────────────────────────────────────────────

def progress_bar(percent: float, width: int = 10) -> str:
    """Return a Unicode progress bar, e.g. ▓▓▓▓░░░░░░ for percent=40, width=10."""
    percent = max(0.0, min(100.0, float(percent)))
    filled = round(percent / 100 * width)
    return "▓" * filled + "░" * (width - filled)


def _fmt_size(size_bytes: int) -> str:
    """Human-readable file size."""
    if size_bytes >= 1_073_741_824:
        return f"{size_bytes / 1_073_741_824:.1f}GB"
    if size_bytes >= 1_048_576:
        return f"{size_bytes / 1_048_576:.0f}MB"
    if size_bytes >= 1024:
        return f"{size_bytes / 1024:.0f}KB"
    return f"{size_bytes}B" if size_bytes else "0 B"


# ── Command response formatters ───────────────────────────────────────────────

def format_health(alerts: list[str]) -> str:
    """
    Produce a /health response with live psutil metrics and ▓░ progress bars.

    Calls psutil.cpu_percent(interval=0.5) — BLOCKING for 0.5 s.
    Run via run_in_executor from the async command handler.

    Thresholds:
      CPU:  > 80% = ⚠️,  > 95% = 🚨
      RAM:  > 80% = ⚠️
      Disk: > 85% = ⚠️,  > 95% = 🚨
    """
    import psutil

    # CPU — actual utilisation, not load average
    cpu_pct = psutil.cpu_percent(interval=0.5)

    # RAM
    mem = psutil.virtual_memory()
    ram_pct      = mem.percent
    ram_used_gb  = mem.used  / 1_073_741_824
    ram_total_gb = mem.total / 1_073_741_824

    # Disk (root filesystem)
    disk     = psutil.disk_usage("/")
    disk_pct = disk.percent

    # Uptime
    uptime_secs = time.time() - psutil.boot_time()
    up_days  = int(uptime_secs // 86400)
    up_hours = int((uptime_secs % 86400) // 3600)
    up_mins  = int((uptime_secs % 3600) // 60)
    if up_days:
        uptime_str = f"{up_days}d {up_hours}h"
    elif up_hours:
        uptime_str = f"{up_hours}h {up_mins}m"
    else:
        uptime_str = f"{up_mins}m"

    # Status icon
    is_crit = cpu_pct > 95 or disk_pct > 95
    is_warn = cpu_pct > 80 or ram_pct > 80 or disk_pct > 85 or bool(alerts)
    status_icon = "🚨" if is_crit else ("⚠️" if is_warn else "✅")
    status_text = "Critical!" if is_crit else ("Warning" if is_warn else "All systems normal")

    # Per-metric icons
    cpu_icon  = "🚨" if cpu_pct > 95  else ("⚠️" if cpu_pct > 80  else "")
    ram_icon  = "⚠️" if ram_pct > 80  else ""
    disk_icon = "🚨" if disk_pct > 95 else ("⚠️" if disk_pct > 85 else "")

    cpu_bar  = progress_bar(cpu_pct)
    ram_bar  = progress_bar(ram_pct)
    disk_bar = progress_bar(disk_pct)

    lines = [
        "🖥 *Health Report*",
        "",
        "```",
        f"CPU   {cpu_bar}  {cpu_pct:.0f}%{' ' + cpu_icon if cpu_icon else ''}",
        f"RAM   {ram_bar}  {ram_used_gb:.1f} / {ram_total_gb:.1f} GB{' ' + ram_icon if ram_icon else ''}",
        f"Disk  {disk_bar}  {disk_pct:.0f}%{' ' + disk_icon if disk_icon else ''}",
        "```",
        "",
        f"{status_icon} {status_text}",
        f"⏱ Uptime: {uptime_str}",
        f"🕐 Next check: 30 min",
    ]

    if alerts:
        lines += ["", "⚠️ *Alerts*"]
        for alert in alerts[:5]:
            lines.append(f"  {alert}")

    return "\n".join(lines)


def format_storage(usage: dict, last_purge: str = "never", has_old_files: bool = False) -> str:
    """
    Format /storage with disk usage bar and per-directory breakdown.
    *usage* is the dict returned by StorageManager.get_disk_usage().
    File list shows only folder name + size — no policy tags (prevents line wrap on mobile).
    """
    total_gb  = usage["total_gb"]
    used_gb   = usage["used_gb"]
    free_gb   = usage["free_gb"]
    used_pct  = (used_gb / total_gb * 100) if total_gb else 0
    dir_sizes = usage.get("dir_sizes", {})

    bar = progress_bar(used_pct, 12)

    if used_pct > 95:
        header = "📊 *Storage 🚨*"
    elif used_pct > 85:
        header = "📊 *Storage ⚠️*"
    else:
        header = "📊 *Storage Report*"

    _DIRS = ["audio", "photos", "documents", "images", "screenshots", "tmp", "backups", "logs"]
    table_lines = [f"📁 {name:<13}{_fmt_size(dir_sizes.get(name, 0)):>7}" for name in _DIRS]
    table = "\n".join(table_lines)

    old_note = "\n\n⚠️ Old files found — /purge to clean" if has_old_files else ""

    return (
        f"{header}\n\n"
        f"💾 `{bar}` {used_pct:.0f}%\n"
        f"{used_gb:.1f} / {total_gb:.0f} GB ({free_gb:.1f} GB free)\n\n"
        f"```\n{table}\n```\n\n"
        f"🕐 Last purge: {last_purge}"
        f"{old_note}"
    )


def format_status(
    ollama_ok: bool,
    hb_running: bool,
    tools_ok: int,
    tools_total: int,
    sub_agent_count: int,
    skill_count: int,
) -> str:
    """Format /status."""
    hb_icon  = "💓" if hb_running else "❌"
    hb_text  = "healthy"  if hb_running else "stopped"
    ol_icon  = "✅" if ollama_ok else "❌"
    ol_text  = "online"   if ollama_ok else "offline"
    return (
        "🤖 *Kovo Status*\n\n"
        f"📡 Gateway: running\n"
        f"{ol_icon} Ollama: {ol_text}\n"
        f"✅ Claude CLI: ready\n"
        f"{hb_icon} Heartbeat: {hb_text}\n\n"
        f"🔧 Tools: {tools_ok}/{tools_total} configured\n"
        f"🤖 Agents: 1 main + {sub_agent_count} sub\n"
        f"📚 Skills: {skill_count} loaded"
    )


def format_memory_log(log_text: str, today_date: date) -> str:
    """
    Parse a daily log file and produce a bulleted activity list.
    Daily log format: each entry is "- [HH:MM] agent=... model=..." followed by
    "  User: text" and "  Reply: text".
    """
    date_str = today_date.strftime("%b %d, %Y")

    bullets: list[str] = []
    lines = log_text.splitlines()
    i = 0
    while i < len(lines):
        ts_m = re.match(r"- \[(\d{1,2}:\d{2})\]", lines[i])
        if ts_m:
            ts = ts_m.group(1)
            user_text = ""
            for j in range(i + 1, min(i + 4, len(lines))):
                user_m = re.match(r"\s+User:\s*(.+)", lines[j])
                if user_m:
                    user_text = user_m.group(1)[:52]
                    break
            bullet = f"• {ts}"
            if user_text:
                bullet += f" {user_text}"
            bullets.append(bullet)
        i += 1

    count = len(bullets)
    recent = bullets[-8:]
    body = "\n".join(recent) if recent else "_No entries yet_"

    return (
        f"🧠 *Today's Memory*\n\n"
        f"📅 {date_str}\n\n"
        f"{body}\n\n"
        f"📝 {count} entr{'y' if count == 1 else 'ies'} | /flush to save"
    )


def format_tools(tools: list) -> str:
    """Format /tools with a ready/needs-config summary line."""
    if not tools:
        return "🔧 No tools registered."

    lines = ["🔧 *Tool Registry*\n"]
    ready = need_cfg = 0
    for t in tools:
        if t.available:
            lines.append(f"✅ *{t.name}* — {t.description}")
            ready += 1
        else:
            lines.append(f"⚙️ *{t.name}* — {t.description}")
            if t.config_needed:
                lines.append(f"  _{t.config_needed}_")
            elif t.install_command:
                lines.append(f"  `{t.install_command}`")
            need_cfg += 1

    parts = []
    if ready:
        parts.append(f"✅ {ready} ready")
    if need_cfg:
        parts.append(f"⚙️ {need_cfg} need config")
    lines += ["", "  ".join(parts)]
    return "\n".join(lines)


def format_skills(skills: list) -> str:
    """Format /skills as a list with a count summary."""
    count = len(skills)
    if not count:
        return "📚 No skills loaded.\n\n_Use /newskill to create one._"

    lines = ["📚 *Skills*\n"]
    for s in skills:
        lines.append(f"• *{s.name}*")
        if s.description:
            lines.append(f"  {s.description}")
        lines.append("")
    lines.append(f"📚 {count} skill{'s' if count != 1 else ''} loaded | /newskill to add")
    return "\n".join(lines)


def format_agents(sub_agents: list) -> str:
    """Format /agents showing the main agent + any sub-agents."""
    lines = ["🤖 *Agents*\n", "Main: *Kovo* ✅", "  Tools: all"]

    if sub_agents:
        lines += ["", f"Sub-agents: {len(sub_agents)}"]
        for a in sub_agents:
            tools_str = ", ".join(a.tools[:4]) if a.tools else "none"
            lines += [f"• *{a.name}* — {a.purpose}", f"  tools: `{tools_str}`"]
    else:
        lines += [
            "",
            "Sub-agents: none",
            "",
            "_💡 I'll recommend one when I notice_",
            "_   repeated specialist requests._",
        ]

    return "\n".join(lines)


def format_permissions(perms: list, pending: dict | None = None) -> str:
    """Format /permissions with truncation for long lists."""
    if not perms:
        return "🔑 No permissions configured."

    count = len(perms)
    MAX_SHOW = 25
    shown = [str(p) for p in perms[:MAX_SHOW]]
    remaining = count - MAX_SHOW

    perm_str = ", ".join(shown)
    if remaining > 0:
        perm_str += f", ... +{remaining} more"

    lines = [f"🔑 *Permissions ({count} entries)*\n", perm_str, ""]

    if pending:
        lines += [f"⏳ *Pending:* `{pending['pattern']}`", "Tap *Approve* or *Deny* below."]
    else:
        lines.append("/approve or /deny pending requests")

    return "\n".join(lines)


def format_purge_review(purgeable: dict) -> str:
    """
    Format the /purge review prompt — shows file counts, sizes, and oldest file age.
    Oldest age is computed from file mtime so scan_purgeable needs no changes.
    """
    import os

    _ICONS = {"photos": "📸", "documents": "📄", "images": "🖼️"}
    now = time.time()

    lines = ["🗑 *Purge Review*\n", "Found old files:\n"]
    total_count = 0
    total_mb    = 0.0

    for dir_name, info in purgeable.items():
        icon = _ICONS.get(dir_name, "📁")
        oldest_days = 0
        for f in info.get("files", []):
            try:
                age = (now - os.path.getmtime(f)) / 86400
                oldest_days = max(oldest_days, int(age))
            except OSError:
                pass
        lines.append(f"{icon} *{dir_name}* — {info['count']} files ({info['total_mb']}MB)")
        if oldest_days:
            lines.append(f"  oldest: {oldest_days} days ago")
        total_count += info["count"]
        total_mb    += info["total_mb"]
        lines.append("")

    lines.append(f"Total: {total_count} files, {total_mb:.1f}MB")
    return "\n".join(lines)
