---
name: server-health
description: Monitor and report on Linux server and Unraid health metrics
tools: [shell]
trigger: server, health, disk, cpu, ram, memory, docker, unraid, array, drive, container, load, storage, uptime, network, process, service
---

# Server Health Skill

## Capabilities
- Check disk usage across all mount points (`df -h`)
- Report RAM and swap usage (`free -h`)
- Show CPU load averages (`/proc/loadavg`)
- List running Docker containers and their status
- Check systemd service status
- Show top CPU/memory-consuming processes
- Report system uptime and load
- Check network interfaces

## Alert Thresholds
- Disk usage > 85% → alert
- CPU load (1-min avg) > 4.0 → alert
- RAM usage > 80% → alert
- Any Docker container in "Exited" or "Restarting" state → alert

## Procedures

### Quick Health Check
1. `df -h` — disk usage
2. `free -h` — memory
3. `cat /proc/loadavg` — CPU load
4. `docker ps --format "table {{.Names}}\t{{.Status}}"` — containers

### Full Health Report
All of the above, plus:
5. `uptime` — system uptime
6. `ps aux --sort=-%cpu | head -10` — top processes
7. `ip -br addr` — network interfaces
8. `systemctl --failed` — failed services

### Response Format
Always summarize findings in plain English. Lead with the most critical issues.
If everything is healthy, say so briefly. Include the raw numbers.

## Infrastructure Context
- This is an Ubuntu 25.10 VM running on an Unraid server
- Ollama NUC is at <OLLAMA-HOST>:11434
- Docker is used heavily — check container health
- The VM has 8GB RAM and 50GB disk
