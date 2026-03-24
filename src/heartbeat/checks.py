"""
System health check functions.
All functions are synchronous (called from APScheduler jobs or agents).
"""
from __future__ import annotations

import json
import logging
import re
import subprocess
import urllib.request

import psutil

log = logging.getLogger(__name__)


def _run(cmd: str, timeout: int = 15) -> str:
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.stdout.strip()
    except Exception as e:
        return f"(error: {e})"


def gather_quick_health() -> str:
    """Fast health snapshot — used by the heartbeat scheduler."""
    parts: list[str] = []

    # Disk — filter to real filesystems
    disk_out = _run("df -h --output=target,size,used,avail,pcent -x tmpfs -x devtmpfs -x udev 2>/dev/null | head -20")
    if disk_out:
        parts.append(f"DISK:\n{disk_out}")

    # Memory
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    parts.append(
        f"MEMORY:\n"
        f"  RAM:  {mem.used // 1024**2}MB / {mem.total // 1024**2}MB  ({mem.percent:.1f}% used)\n"
        f"  Swap: {swap.used // 1024**2}MB / {swap.total // 1024**2}MB  ({swap.percent:.1f}% used)"
    )

    # CPU
    load1, load5, load15 = psutil.getloadavg()
    cpu_count = psutil.cpu_count()
    parts.append(
        f"CPU LOAD: {load1:.2f} / {load5:.2f} / {load15:.2f}  "
        f"(1/5/15 min, {cpu_count} cores)"
    )

    # Docker
    docker_out = _run(
        'docker ps --format "table {{.Names}}\t{{.Status}}" 2>/dev/null || echo "docker unavailable"'
    )
    if docker_out:
        parts.append(f"DOCKER:\n{docker_out}")

    return "\n\n".join(parts)


def gather_full_health() -> str:
    """Comprehensive health report — used by 6-hour heartbeat and full reports."""
    parts = [gather_quick_health()]

    # Uptime
    uptime_out = _run("uptime -p 2>/dev/null || uptime")
    parts.append(f"UPTIME: {uptime_out}")

    # Top processes by CPU
    top_cpu = _run("ps aux --sort=-%cpu | head -8 | awk '{print $1,$3,$4,$11}'")
    if top_cpu:
        parts.append(f"TOP PROCESSES (CPU):\n{top_cpu}")

    # Network interfaces
    net_out = _run("ip -br addr show 2>/dev/null | grep -v '^lo'")
    if net_out:
        parts.append(f"NETWORK:\n{net_out}")

    # Failed systemd services
    failed = _run("systemctl --failed --no-legend 2>/dev/null | head -5")
    if failed:
        parts.append(f"FAILED SERVICES:\n{failed}")
    else:
        parts.append("FAILED SERVICES: none")

    # Disk I/O
    io = psutil.disk_io_counters()
    if io:
        parts.append(
            f"DISK I/O: read={io.read_bytes // 1024**2}MB  write={io.write_bytes // 1024**2}MB"
        )

    return "\n\n".join(parts)


def fetch_weather(location: str = "Al Ain, UAE", timeout: int = 10) -> str:
    """
    Fetch current weather for *location* using wttr.in (no API key needed).
    Returns a compact one-line summary, e.g.:
      ☀️ 38°C (feels 41°C) · Sunny · Humidity 18% · Wind 14 km/h · High 40 / Low 27°C
    Falls back to an error string if the request fails.
    """
    try:
        url = f"https://wttr.in/{urllib.request.quote(location)}?format=j1"
        req = urllib.request.Request(url, headers={"User-Agent": "MiniClaw/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())

        cur = data["current_condition"][0]
        today = data["weather"][0]

        temp = cur.get("temp_C", "?")
        feels = cur.get("FeelsLikeC", "?")
        desc = cur["weatherDesc"][0]["value"] if cur.get("weatherDesc") else "?"
        humidity = cur.get("humidity", "?")
        wind = cur.get("windspeedKmph", "?")
        hi = today.get("maxtempC", "?")
        lo = today.get("mintempC", "?")

        # Pick a representative emoji
        desc_lower = desc.lower()
        if "sun" in desc_lower or "clear" in desc_lower:
            icon = "☀️"
        elif "cloud" in desc_lower or "overcast" in desc_lower:
            icon = "⛅"
        elif "rain" in desc_lower or "drizzle" in desc_lower:
            icon = "🌧️"
        elif "thunder" in desc_lower or "storm" in desc_lower:
            icon = "⛈️"
        elif "sand" in desc_lower or "dust" in desc_lower:
            icon = "🌫️"
        elif "fog" in desc_lower or "mist" in desc_lower:
            icon = "🌁"
        else:
            icon = "🌡️"

        return (
            f"{icon} {temp}°C (feels {feels}°C) · {desc} · "
            f"Humidity {humidity}% · Wind {wind} km/h · "
            f"High {hi} / Low {lo}°C"
        )
    except Exception as e:
        log.warning("Weather fetch failed for %s: %s", location, e)
        return f"(weather unavailable: {e})"


def check_thresholds(health_data: str) -> list[str]:
    """
    Scan health data for threshold violations.
    Returns list of human-readable alert strings (empty = all clear).
    """
    alerts: list[str] = []

    # Disk usage > 85%
    for match in re.finditer(r"(\d+)%", health_data):
        pct = int(match.group(1))
        if pct > 85:
            # Get context (the line containing this %)
            start = health_data.rfind("\n", 0, match.start()) + 1
            end = health_data.find("\n", match.end())
            line = health_data[start:end].strip()
            alerts.append(f"⚠️ High disk usage ({pct}%): {line[:80]}")

    # CPU load > 4.0
    load_match = re.search(r"LOAD:\s+([\d.]+)\s*/\s*([\d.]+)", health_data)
    if load_match:
        load1 = float(load_match.group(1))
        if load1 > 4.0:
            alerts.append(f"⚠️ High CPU load: {load1:.2f} (1-min avg)")

    # RAM > 80%
    ram_match = re.search(r"RAM:.*?\(([\d.]+)% used\)", health_data)
    if ram_match:
        ram_pct = float(ram_match.group(1))
        if ram_pct > 80:
            alerts.append(f"⚠️ High RAM usage: {ram_pct:.1f}%")

    # Docker containers in bad state
    for state in ("Exited", "Restarting", "Dead"):
        if state in health_data:
            alerts.append(f"⚠️ Docker container in {state} state")

    # Failed systemd services
    failed_match = re.search(r"FAILED SERVICES:\n(.+)", health_data)
    if failed_match and failed_match.group(1).strip() != "none":
        alerts.append(f"⚠️ Failed systemd services: {failed_match.group(1)[:100]}")

    return alerts
