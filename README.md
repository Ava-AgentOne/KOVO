<div align="center">

<img src="https://raw.githubusercontent.com/Ava-AgentOne/kovo/main/kovo-mascot.png" alt="Kovo" width="280">

# 👾 Kovo

**Your Self-Hosted AI Agent for Ubuntu**

[![GitHub release](https://img.shields.io/github/v/release/Ava-AgentOne/kovo?color=378ADD&label=Release)](https://github.com/Ava-AgentOne/kovo/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![Ubuntu](https://img.shields.io/badge/Ubuntu-24.04+-E95420?logo=ubuntu&logoColor=white)](https://ubuntu.com)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-26A5E4?logo=telegram&logoColor=white)](https://core.telegram.org/bots)

*A personal AI assistant that lives on your VM — chat via Telegram, monitor via dashboard, extend with skills.*

---

</div>

## 📖 What Is Kovo?

**Kovo** is a self-hosted AI agent that runs on an Ubuntu VM and communicates with you through **Telegram**. It can manage your server, run security audits, browse the web, make phone calls, read your Google Drive, and learn new skills — all while keeping your data private on your own hardware.

Think of it as your own AI assistant that lives on your home lab, with a clean web dashboard to monitor everything.

### 🎯 Who Is This For?

- **Home lab enthusiasts** who want a personal AI agent on their own hardware
- **Developers** looking for an extensible, self-hosted AI platform
- **Privacy-conscious users** who want AI without cloud dependencies
- Anyone who wants to **automate** server management via natural language

## ✨ Features

| Feature | Description |
|---------|-------------|
| 💬 **Telegram Chat** | Talk to Kovo through Telegram with persistent keyboard buttons |
| 🖥️ **Web Dashboard** | Real-time system monitoring with dark/light mode |
| 🛡️ **Security Audits** | Automated port scanning, malware checks, rootkit detection |
| 🧠 **Memory System** | Daily logs, learnings, and long-term memory across sessions |
| ⚡ **Skill System** | Modular skills — browse web, shell commands, phone calls, reports |
| 🤖 **Sub-Agents** | Spawn specialized agents for recurring tasks |
| 📊 **Health Monitoring** | CPU, RAM, disk, uptime — all visible from dashboard and Telegram |
| 🔧 **Tool Registry** | Ollama, Google Drive, Gmail, shell, browser — all managed centrally |
| 💾 **Heartbeat** | Scheduled checks: morning briefing, evening summary, weekly audit |
| 📞 **Voice Calls** | Real Telegram voice calls for critical alerts |

## 🖥️ Dashboard

The built-in web dashboard gives you full visibility into Kovo's state:

| Section | What It Shows |
|---------|---------------|
| 📡 **Overview** | CPU, RAM, disk metrics + service status dots + quick actions |
| 💬 **Chat** | Talk to Kovo from the browser (WebSocket) |
| 🔧 **Tools** | All registered tools with status and install commands |
| 🤖 **Agents** | Main agent + any sub-agents with their tools |
| 🧠 **Memory** | Browse daily logs and workspace files |
| ⚡ **Skills** | View, create, delete skills + ClawHub marketplace |
| 💓 **Heartbeat** | Scheduled job status and health reports |
| 🛡️ **Security** | Latest audit results, history, run/reset from UI |
| 📜 **Logs** | Live gateway logs |
| ⚙️ **Settings** | YAML config editor + environment variables |

## 🚀 Quick Start

### Prerequisites

- Ubuntu 24.04+ VM (tested on Unraid)
- 4GB+ RAM, 20GB+ disk
- Telegram Bot Token ([create one](https://t.me/BotFather))
- Your Telegram User ID ([find yours](https://t.me/userinfobot))

### One-Line Install

```bash
curl -fsSL https://raw.githubusercontent.com/Ava-AgentOne/kovo/main/bootstrap.sh | bash
```

This will:
1. Clone the repo to `/opt/kovo`
2. Install Python 3.11+, Node 22, system dependencies
3. Create a Python virtual environment with all packages
4. Build the dashboard frontend
5. Set up the systemd service

### Configure

```bash
cd /opt/kovo/config
cp .env.example .env
nano .env
```

Fill in your credentials:

```env
TELEGRAM_BOT_TOKEN=your-bot-token
OWNER_TELEGRAM_ID=your-telegram-id
OLLAMA_HOST=http://192.168.1.212:11434
```

### Start

```bash
sudo systemctl enable --now kovo
```

Open the dashboard at `http://<YOUR-VM-IP>:8080/dashboard`

## 📱 Telegram Commands

Kovo uses a persistent reply keyboard with emoji buttons:

| Button | Command | What It Does |
|--------|---------|--------------|
| 📡 Status | `/status` | Service status — tools, skills, agents |
| 🖥️ Health | `/health` | CPU %, RAM in GB, disk usage |
| 🧠 Memory | `/memory` | Today's session log |
| 💾 Storage | `/storage` | File storage usage with gauge |
| 📚 Skills | `/skills` | List all loaded skills |
| 🔧 Tools | `/tools` | Tool registry with status |

Plus: `/agents`, `/permissions`, `/purge`, and natural language for everything else.

## ⚡ Skills

Kovo ships with built-in skills and supports custom ones:

| Skill | Description |
|-------|-------------|
| 🌐 **browser** | Navigate pages, take screenshots, fill forms |
| 💬 **general** | Conversation, reasoning, planning |
| 📂 **google** | Google Docs, Drive, Gmail, Spreadsheets |
| 📞 **phone-call** | Real Telegram voice calls + TTS voice messages |
| 📊 **report-builder** | Generate HTML reports with charts |
| 🛡️ **security-audit** | Deep security scan — ports, users, malware |
| 🖥️ **server-health** | Linux server and Unraid health metrics |
| ⚙️ **shell** | Execute commands, manage files, install packages |

### Create Custom Skills

Drop a `SKILL.md` file in `workspace/skills/<name>/` with frontmatter:

```yaml
---
name: my-skill
description: What this skill does
tools: [shell, browser]
trigger: keyword1, keyword2, keyword3
---

# My Skill

Instructions for how Kovo should use this skill...
```

## 🏗️ Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Telegram    │────▶│   Gateway    │────▶│   Ollama    │
│  (Mobile)    │◀────│  (FastAPI)   │◀────│  (NUC LLM)  │
└─────────────┘     └──────┬───────┘     └─────────────┘
                           │
                    ┌──────┴───────┐
                    │  Dashboard   │
                    │  (React UI)  │
                    └──────────────┘
```

| Component | Technology |
|-----------|-----------|
| **Gateway** | Python 3.11, FastAPI, Uvicorn |
| **Telegram** | python-telegram-bot |
| **LLM** | Ollama (Llama, Qwen, etc.) |
| **Dashboard** | React, Vite, Tailwind CSS, Lucide Icons |
| **Database** | SQLite (sessions, audit logs) |
| **Voice** | py-tgcalls + FFmpeg for Telegram calls |

## ⚙️ Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | ✅ | Bot token from @BotFather |
| `OWNER_TELEGRAM_ID` | ✅ | Your Telegram user ID |
| `OLLAMA_HOST` | ❌ | Ollama URL (default: `http://localhost:11434`) |
| `GROQ_API_KEY` | ❌ | Groq cloud API for fast inference |
| `GITHUB_TOKEN` | ❌ | GitHub access for ClawHub skill marketplace |

## 🛡️ Security

Kovo includes built-in security features:

- **Token masking** — all API keys masked in log output
- **`.env` validation** — fails fast if required vars are missing or placeholder
- **File permissions** — `.env`, credentials, and DB set to `chmod 600`
- **Shell blocklist** — dangerous commands blocked or require confirmation
- **Security audits** — automated port scan, user check, ClamAV, chkrootkit

## 📁 Project Structure

```
/opt/kovo/
├── config/          # .env, settings.yaml, credentials
├── data/            # SQLite DB, security audit data, temp files
├── scripts/         # Helper scripts
├── src/
│   ├── agents/      # Main agent + sub-agent runner
│   ├── dashboard/   # FastAPI API + React frontend
│   ├── heartbeat/   # Scheduled tasks
│   ├── memory/      # Memory system
│   ├── skills/      # Skill registry + loader
│   └── tools/       # Tool registry (Ollama, Google, Shell, etc.)
├── workspace/
│   ├── memory/      # Daily log files (YYYY-MM-DD.md)
│   ├── skills/      # Skill definitions (SKILL.md per skill)
│   ├── SOUL.md      # Agent personality
│   ├── IDENTITY.md  # Agent identity card
│   └── MEMORY.md    # Long-term learnings
├── bootstrap.sh     # One-line installer
├── requirements.txt # Python dependencies
└── README.md        # You are here
```

## 🔍 Troubleshooting

<details>
<summary><strong>Dashboard shows "Not Found" at port 8080</strong></summary>

The dashboard is served at `/dashboard`, not the root. Navigate to `http://<IP>:8080/dashboard`.
</details>

<details>
<summary><strong>Telegram bot not responding</strong></summary>

- Check your `TELEGRAM_BOT_TOKEN` is correct in `.env`
- Verify `OWNER_TELEGRAM_ID` matches your Telegram user ID
- Check logs: `journalctl -u kovo -f`
</details>

<details>
<summary><strong>Ollama shows "Offline" in dashboard</strong></summary>

- Verify `OLLAMA_HOST` points to your running Ollama instance
- Test connectivity: `curl http://<OLLAMA_IP>:11434/api/tags`
- Ensure the VM can reach the Ollama host (check firewall/network)
</details>

<details>
<summary><strong>Security audit fails</strong></summary>

- Install ClamAV: `sudo apt install clamav`
- Install chkrootkit: `sudo apt install chkrootkit`
- The audit still runs without these — it just reports "not_installed"
</details>

## 📜 License

[MIT](LICENSE) — Use it, modify it, share it.

---

<div align="center">

**Built for home labs** · Powered by [Ollama](https://ollama.com) + [FastAPI](https://fastapi.tiangolo.com/) · Chat via [Telegram](https://telegram.org)

Made with 💙 by [Ava-AgentOne](https://github.com/Ava-AgentOne)

</div>
