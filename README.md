<div align="center">

<img src="https://raw.githubusercontent.com/Ava-AgentOne/kovo/main/kovo-logo.svg" alt="Kovo" width="180">

# <span style="color:#378ADD">KOVO</span>

**Your Self-Hosted AI Agent for Linux & macOS**

[![GitHub release](https://img.shields.io/github/v/release/Ava-AgentOne/kovo?color=378ADD&label=Release)](https://github.com/Ava-AgentOne/kovo/releases)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.13+-3776AB?logo=python&logoColor=white)](https://python.org)
[![Claude Code](https://img.shields.io/badge/Claude_Code-Powered-DA7756?logo=anthropic&logoColor=white)](https://docs.anthropic.com/en/docs/claude-code)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-26A5E4?logo=telegram&logoColor=white)](https://core.telegram.org/bots)
[![Ko-fi](https://img.shields.io/badge/Ko--fi-Support_KOVO-FF5E5B?logo=ko-fi&logoColor=white)](https://ko-fi.com/erumaithi)

*A personal AI agent powered by Claude Code — chat via Telegram, monitor via dashboard, extend with skills.*

---

</div>

## 📖 What Is KOVO?

**KOVO** is a self-hosted AI agent powered by **[Claude Code](https://docs.anthropic.com/en/docs/claude-code)** that runs on a Linux VM or macOS machine and communicates with you through **Telegram**. It can manage your server, run security audits, browse the web, make phone calls, read your Google Drive, and learn new skills — all while keeping your data private on your own hardware.

Inspired by **[OpenClaw](https://github.com/openclaw)**, KOVO takes a different approach to the AI backbone — it uses **Claude Code CLI as a subprocess** (`claude -p`), powered by your Claude Max subscription. This gives it access to Claude Sonnet and Opus for real multi-step reasoning, not pay-per-token API calls. It optionally uses a **local LLM** (like [Ollama](https://ollama.com)) for cheap tasks like heartbeats and quick classification.

### 🧠 Why Claude Code?

Most self-hosted agents rely on basic API calls to an LLM. KOVO is different — it uses **Claude Code as a subprocess** (`claude -p`), which means:

- **Full Claude reasoning** — Sonnet for medium tasks, Opus for complex ones
- **Smart model routing** — local LLM handles simple tasks (free), Claude handles the rest
- **Tool use** — Claude Code can execute shell commands, edit files, and reason about code
- **No API key management** — uses your Claude Max/Pro subscription directly
- **Self-evolving** — the agent can install packages, create services, and write new skills

### 🎯 Who Is This For?

- **Home lab enthusiasts** who want a personal AI agent on their own hardware
- **Developers** looking for an extensible, Claude-powered AI platform
- **Privacy-conscious users** who want AI without cloud data storage
- Anyone who wants to **automate** server management via natural language

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🧠 **Claude Code Backbone** | Full Claude Sonnet/Opus reasoning via `claude -p` subprocess |
| 💬 **Telegram Chat** | Talk to KOVO through Telegram with persistent keyboard buttons |
| 🖥️ **Web Dashboard** | Real-time system monitoring with dark/light mode |
| 🛡️ **Security Audits** | Automated port scanning, malware checks, rootkit detection |
| 🧠 **Memory System** | Daily logs, learnings, and long-term memory across sessions |
| ⚡ **Skill System** | Modular skills — browse web, shell commands, phone calls, reports |
| 🤖 **Sub-Agents** | Spawn specialized agents for recurring tasks |
| 📊 **Health Monitoring** | CPU, RAM, disk, uptime — all visible from dashboard and Telegram |
| 🔧 **Smart Model Router** | Local LLM for simple tasks, Claude for complex ones |
| 📞 **Voice Calls** | Real Telegram voice calls for critical alerts |
| 🔍 **Web Search** | Auto DuckDuckGo search for current-info questions |
| 🔗 **Link Reader** | Auto-extracts page content from URLs in messages |
| ⏰ **Smart Reminders** | SQLite-backed reminders with message, call, or both delivery |

## 🏗️ Architecture

```
                    ┌──────────────────┐
                    │   Claude Code    │  ← The Brain
                    │  (claude -p CLI) │
                    │  Sonnet / Opus   │
                    └────────┬─────────┘
                             │
┌─────────────┐     ┌───────┴────────┐     ┌──────────────┐
│  Telegram   │────▶│    Gateway     │────▶│  Local LLM   │
│  (Mobile)   │◀────│   (FastAPI)    │◀────│  (Optional)  │
└─────────────┘     └───────┬────────┘     └──────────────┘
                            │
                     ┌──────┴───────┐
                     │  Dashboard   │
                     │  (React UI)  │
                     └──────────────┘
```

| Component | Technology |
|-----------|-----------|
| **Brain** | Claude Code CLI (`claude -p`) — Sonnet & Opus |
| **Gateway** | Python 3.13, FastAPI, Uvicorn |
| **Telegram** | python-telegram-bot |
| **Local LLM** | Ollama, LM Studio, or any OpenAI-compatible endpoint (optional) |
| **Dashboard** | React, Vite, Tailwind CSS, Lucide Icons |
| **Database** | SQLite (memories, reminders, heartbeat log, permissions, stats) |
| **Voice** | py-tgcalls + FFmpeg for Telegram calls |

### Smart Model Router

KOVO intelligently routes messages to the right model:

| Complexity | Routed To | Use Case |
|------------|-----------|----------|
| **Simple** | Claude Sonnet | Quick Q&A, greetings, status checks |
| **Medium** | Claude Sonnet | Most tasks, code, analysis |
| **Complex** | Claude Opus | Deep reasoning, architecture, planning |

> Local LLM (Ollama) is used exclusively for heartbeat health summaries — never in the message routing path.

## 🖥️ Dashboard

The built-in web dashboard gives you full visibility into KOVO's state:

| Section | What It Shows |
|---------|---------------|
| 📡 **Overview** | CPU, RAM, disk metrics + service status dots + quick actions |
| 💬 **Chat** | Talk to KOVO from the browser (WebSocket) |
| 🔧 **Tools** | All registered tools with status and install commands |
| 🤖 **Agents** | Main agent + any sub-agents with their tools |
| 🧠 **Memory** | Browse daily logs and workspace files |
| ⚡ **Skills** | View, create, delete, and reload skills |
| 💓 **Heartbeat** | Scheduled job status and health reports |
| 🛡️ **Security** | Latest audit results, history, run/reset from UI |
| 📜 **Logs** | Live gateway logs |
| ⚙️ **Settings** | YAML config editor + environment variables |
| 🧙 **Setup Wizard** | First-time guided configuration with step-by-step credential guides |

## 🚀 Quick Start

### Prerequisites

- **Linux** — Ubuntu 24.04+, Debian 12+, or similar (tested on Unraid)
- **macOS** — macOS 13 Ventura or newer
- **4GB+ RAM**, **30GB+ disk**
- **Claude Max** or **Team** subscription — [sign up](https://claude.ai)

> The installer handles everything else — Claude Code CLI, Node.js, Python, Homebrew (macOS), and all dependencies.

### One-Line Install

```bash
curl -fsSL https://raw.githubusercontent.com/Ava-AgentOne/kovo/main/bootstrap.sh -o /tmp/kovo-install.sh
bash /tmp/kovo-install.sh
```

This will:
1. Check your system meets requirements
2. Install Python 3.13+, Node 22, system dependencies
3. Create a Python virtual environment with all packages
4. Build the dashboard frontend
5. Set up Claude Code permissions
6. Set up the service (systemd on Linux, launchd on macOS)
7. Launch the **Dashboard** for easy configuration

### Configure & Start

**Linux:**
```bash
sudo systemctl enable --now kovo
```

**macOS:**
```bash
launchctl load ~/Library/LaunchAgents/com.kovo.agent.plist
```

Open the **Dashboard** in your browser:

```
http://<YOUR-IP>:8080/dashboard
```

On first run (or when `.env` is unconfigured), the dashboard automatically redirects to the **Setup Wizard** at `/dashboard/setup`. The wizard walks you through:
- **Telegram** — bot token + your user ID (with links to @BotFather and @userinfobot)
- **Google Workspace** — which APIs to enable, with direct links to each one
- **Voice Calls** — clear 3-account explanation (your main account, the bot, the caller)
- **Groq Transcription** — free tier setup at console.groq.com

Credentials are saved to `config/.env` on your machine — never transmitted.

> **Prefer manual setup?** Copy `config/.env.template` to `config/.env` and fill in your tokens, then restart the service.

### Upgrade

KOVO has a built-in update mechanism. From the dashboard (Settings → Updates), click **Check for Updates** and **Apply Update**. Or from the command line:

```bash
# Check if an update is available
bash scripts/update.sh --check

# Apply the update (auto-backup, pull, rebuild, restart)
bash scripts/update.sh --apply
```

Updates only trigger on version bumps, not every commit. Your personal data (workspace files, settings, `.env`, database) is never overwritten.

## 📱 Telegram Commands

KOVO uses a persistent reply keyboard with emoji buttons:

| Button | Command | What It Does |
|--------|---------|--------------|
| 📡 Status | `/status` | Service status — tools, skills, agents |
| 🖥️ Health | `/health` | CPU %, RAM in GB, disk usage |
| 🧠 Memory | `/memory` | Today's session log |
| 💾 Storage | `/storage` | File storage usage with gauge |
| 📚 Skills | `/skills` | List all loaded skills |
| 🔧 Tools | `/tools` | Tool registry with status |

Plus: `/agents`, `/permissions`, `/purge`, `/reminders`, `/remind cancel <id>`, `/search`, `/call`, `/db`, and natural language for everything else.

## ⚡ Skills

KOVO ships with built-in skills and supports custom ones:

| Skill | Description |
|-------|-------------|
| 🌐 **browser** | Navigate pages, take screenshots, fill forms |
| 📂 **google-workspace** | Google Docs, Drive, Gmail, Calendar, Sheets |
| 📞 **phone-call** | Real Telegram voice calls + TTS voice messages |
| 📊 **report-builder** | Generate HTML reports with charts |
| 🛡️ **security-audit** | Deep security scan — ports, users, malware |
| 🖥️ **server-health** | System health metrics |
| 🔍 **web-search** | Auto DuckDuckGo search for current-info questions |
| ⏰ **reminders** | Smart reminders with message, call, or both delivery |

## 🛡️ Security

KOVO includes built-in security features:

- **Token masking** — all API keys masked in log output
- **`.env` validation** — warns if required vars are missing; starts in dashboard-only mode
- **File permissions** — `.env`, credentials, and DB set to `chmod 600`
- **Shell blocklist** — dangerous commands blocked or require confirmation
- **Security audits** — automated port scan, user check, ClamAV, chkrootkit
- **Pre-push git hook** — blocks personal data, `.env`, credentials, and database files from being committed
- **Personal data isolation** — repo ships `.template` files only; live workspace files are gitignored
- **Claude Code sandbox** — pre-approved command allowlist, runtime approval via Telegram
- **Shell metachar blocking** — `;|&$\`><(){}!` blocked in all API command endpoints
- **Env key whitelist** — dashboard can only write 9 approved KOVO configuration keys
- **Backup validation** — tar archives checked for path traversal and source code injection before extraction
- **Reminder date validation** — rejects invalid dates that would fire immediately

## 📁 Project Structure

```
<KOVO_DIR>/              # /opt/kovo (Linux) or ~/.kovo (macOS)
├── config/          # .env, settings.yaml, credentials
├── data/            # SQLite DB, security audit data, temp files
├── scripts/         # Helper scripts
├── src/
│   ├── agents/      # Main agent + sub-agent runner
│   ├── dashboard/   # FastAPI API + React frontend
│   ├── gateway/     # FastAPI app, startup, config
│   ├── heartbeat/   # Scheduled tasks (APScheduler)
│   ├── memory/      # Memory system (MD + SQLite)
│   ├── onboarding/  # First-run guided setup
│   ├── router/      # Smart model router (local LLM / Claude)
│   ├── skills/      # Skill registry + loader
│   ├── telegram/    # Bot, commands, formatting
│   ├── tools/       # Tool registry (Claude CLI, shell, browser, etc.)
│   └── utils/       # Cross-platform helpers (platform.py, tz.py)
├── workspace/
│   ├── memory/              # Daily log files (YYYY-MM-DD.md)
│   ├── skills/              # Skill definitions (SKILL.md per skill)
│   ├── SOUL.md.template     # Agent personality (template)
│   ├── USER.md.template     # Owner profile (template)
│   └── MEMORY.md.template   # Long-term learnings (template)
├── bootstrap.sh     # One-line installer
├── requirements.txt # Python dependencies
└── README.md        # You are here
```

## 🆚 KOVO vs OpenClaw

KOVO is inspired by [OpenClaw](https://github.com/openclaw) and uses a compatible workspace format. The key difference is how they connect to AI:

| | KOVO | OpenClaw |
|---|------|----------|
| **AI connection** | Claude Code CLI (`claude -p`) | Direct API calls (OpenAI, Anthropic, etc.) |
| **Billing** | Flat rate — Claude Max subscription (~$100-200/mo) | Pay per token — costs vary with usage |
| **Models** | Claude Sonnet & Opus via Claude Code | Any provider (OpenAI, Anthropic, Groq, local) |
| **Local LLM** | Optional — for heartbeats & cheap tasks | Core — primary model for many setups |
| **Workspace format** | SOUL.md, MEMORY.md, SKILL.md — compatible | ✅ Same format |
| **Platform** | Linux + macOS (self-hosted) | Linux VM (self-hosted) |

KOVO's approach means predictable monthly costs and access to Claude's full reasoning capabilities through Claude Code, while OpenClaw offers more flexibility in model choice and provider.

## 🔍 Troubleshooting

<details>
<summary><strong>Dashboard shows "Not Found" at port 8080</strong></summary>

The dashboard is served at `/dashboard`, not the root. Navigate to `http://<IP>:8080/dashboard`.
</details>

<details>
<summary><strong>Telegram bot not responding</strong></summary>

- Check your `TELEGRAM_BOT_TOKEN` is correct in `.env`
- Verify `OWNER_TELEGRAM_ID` matches your Telegram user ID
- Check logs: `tail -f logs/gateway.log` or `journalctl -u kovo -f` (Linux)
</details>

<details>
<summary><strong>Claude Code not working</strong></summary>

- Verify Claude Code is installed: `claude --version`
- Check authentication: `claude auth status`
- Ensure you have an active Claude Max or Pro subscription
- Check the sandbox permissions: `cat .claude/settings.local.json`
</details>

<details>
<summary><strong>Local LLM shows "Offline" in dashboard</strong></summary>

- Verify your LLM server is running and reachable
- Test connectivity: `curl http://<LLM-HOST>:11434/api/tags`
- Check `OLLAMA_HOST` in your `.env` file
</details>

<details>
<summary><strong>Security audit fails</strong></summary>

- Install ClamAV: `sudo apt install clamav`
- Install chkrootkit: `sudo apt install chkrootkit`
- The audit still runs without these — it just reports "not_installed"
</details>

<details>
<summary><strong>macOS: Gateway crashes on startup</strong></summary>

- Without Telegram tokens configured, the gateway starts in **dashboard-only mode** — this is normal
- Configure `.env` via the Setup Wizard at `http://localhost:8080/dashboard/setup`
- Once Telegram tokens are set, restart the service
</details>

## 📜 License

[GNU AGPLv3](LICENSE) — Free to use, modify, and share. Derivative works must remain open source.

---

<div align="center">

**Built for home labs** · Powered by [Claude Code](https://docs.anthropic.com/en/docs/claude-code) + [FastAPI](https://fastapi.tiangolo.com/) · Chat via [Telegram](https://telegram.org)

Made with 💙 by [Ava-AgentOne](https://github.com/Ava-AgentOne)

[![Ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/erumaithi)

</div>
