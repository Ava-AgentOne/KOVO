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

*A personal AI agent powered by Claude Code — chat via Telegram, run scheduled Routines, talk by voice, extend with skills.*

---

</div>

## 📖 What Is KOVO?

**KOVO** is a self-hosted AI agent powered by **[Claude Code](https://docs.anthropic.com/en/docs/claude-code)** that runs on a Linux VM or macOS machine and communicates with you through **Telegram**. It can manage your server, run security audits, browse the web, make phone calls, read your Google Drive, run recurring **Routines** on a schedule, and **learn new skills with your approval** — all while keeping your data private on your own hardware.

Inspired by **[OpenClaw](https://github.com/openclaw)**, KOVO takes a different approach to the AI backbone — since v2.0 it runs on the **[Claude Agent SDK](https://docs.anthropic.com/en/api/agent-sdk/overview)** (in-process, streaming, native tool use), powered by your Claude Max subscription. This gives it Claude Sonnet and Opus for real multi-step reasoning at a flat rate, not pay-per-token API calls. The classic `claude -p` subprocess remains as a config-selectable fallback, and an optional **local LLM** (like [Ollama](https://ollama.com)) handles cheap tasks like heartbeat summaries.

**v3.0 is the Autonomy Release.** Everything through v2.1 made KOVO an agent you *talk to*. v3.0 makes it an agent that **runs your day** (Routines), **speaks with you** (voice-note conversations, plus an experimental Live Call mode), and **gets smarter on its own** (owner-approved skill learning) — with off-site backups and a guided Add-ons page rounding out the self-hosting story.

### 🧠 Why the Claude Agent SDK?

Most self-hosted agents rely on basic API calls to an LLM. KOVO runs Claude through the **Agent SDK**, which means:

- **Full Claude reasoning** — Sonnet for medium tasks, Opus for complex ones
- **Live streaming replies** — watch answers appear in Telegram (message edits) and the dashboard
- **Real tool use** — Claude calls KOVO's tools natively (phone calls, images, reminders, routines) and reacts to their results
- **MCP integrations** — connect Home Assistant, GitHub, and any Model Context Protocol server; install more from the built-in Store
- **No API key management** — uses your Claude Max/Pro subscription directly
- **Self-evolving** — the agent can install packages, create services, and propose new skills (you approve them)
- **Pluggable by design** — brains (AI backends) and channels (chat surfaces) are config, not code

### 🎯 Who Is This For?

- **Home lab enthusiasts** who want a personal AI agent on their own hardware
- **Developers** looking for an extensible, Claude-powered AI platform
- **Privacy-conscious users** who want AI without cloud data storage
- Anyone who wants to **automate** server management via natural language

## 🆕 What's New in v3.0

| Headline | What It Means |
|----------|---------------|
| ⏰ **Kovo Routines** | Recurring autonomous tasks. Say "check my email every Sunday at 9" — Claude converts it to a cron schedule, runs the task through the full agent on time, and delivers the result to your chat. Each routine keeps its own conversation memory across runs, so "what changed since last time?" actually works. Manage them by chat or from the new dashboard Routines page (presets or custom cron, Run now, per-run history). |
| 🎓 **Auto-Skill Learning** | When a topic keeps coming up and no installed skill covers it, KOVO drafts a new skill in the background and asks you first — Telegram inline buttons or a pending queue on the dashboard, with a full preview. **Nothing ever self-activates**: max 2 proposals a day, a rejected topic is never proposed again, and learned skills carry a 🎓 provenance badge. |
| 🎙️ **Voice Conversations** | Send KOVO a voice message and it replies with a spoken voice note (plus the full text). Replies are speech-shaped — no markdown or URLs read aloud — with a `voice.reply_in_kind` toggle (default on). And behind an opt-in flag: 🧪 **Live Call**, a real-time phone conversation with KOVO. |
| 🧪 **Live Call (experimental)** | `/livecall` or "call me and let's talk" — KOVO rings you on Telegram, listens (voice-activity detection), thinks, and speaks back, walkie-talkie style (~3–6 s per turn in v1). Say "goodbye" to hang up. **Off by default** — enable with `experimental.live_call: true` in `settings.yaml`. |
| 🧩 **Add-ons Page** | Guided one-click setup for system-level companions — Tailscale (remote access), Google Workspace, Ollama, Home Assistant. Each card shows live status (not installed → installed → ready), and every install **shows you the exact commands before anything runs**, with a live log while it works. |
| ☁️ **Off-Site Backups** | Nightly upload of the latest core backup to a "KOVO Backups" folder in **your own Google Drive**, pruned to the last 7 (configurable). Quiet on success, Telegram alert on failure. |
| 🔑 **Google Dashboard Sign-In (optional)** | Alongside the Telegram-approved login: "Sign in with Google", restricted to a single owner-allowlisted account. Hidden until fully configured via env vars — Telegram login remains the default. |

Also in v3.0: the voice-call stack migrated to actively maintained packages (pyrofork + current py-tgcalls), the Telegram **bot command menu** is registered (commands autocomplete when you type `/`), a 📞 Live Call button joins the persistent keyboard, and a long-standing scheduler bug that prevented reminders from firing was found and fixed.

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🧠 **Claude Agent SDK Backbone** | Full Sonnet/Opus reasoning, in-process, with streaming + native tool use (CLI subprocess fallback) |
| ⏰ **Routines** | User-defined recurring autonomous tasks — natural language in, cron-scheduled agent runs out |
| 🎓 **Auto-Skill Learning** | KOVO drafts skills for repeated topics — owner-approved, never self-activating |
| 🎙️ **Voice Conversations** | Voice note in → spoken voice note back; 🧪 experimental Live Call for real-time conversations |
| 💬 **Telegram Chat** | Talk to KOVO through Telegram with persistent keyboard buttons and command autocomplete |
| 🖥️ **Mission Control Dashboard** | Live activity feed, "Kovo is working on…" indicator, 24h sparklines, quick-chat — Telegram-approved login (optional Google sign-in) |
| 🔌 **MCP Integrations + Store** | Connect any MCP server (Home Assistant verified); browse a curated catalog or search the official registry live |
| 🧩 **Add-ons** | Guided companion setup — Tailscale, Google Workspace, Ollama, Home Assistant — commands shown before they run |
| ☁️ **Off-Site Backups** | Nightly backup upload to your own Google Drive with pruning and failure alerts |
| 🛡️ **Security Audits** | Automated port scanning, malware checks, rootkit detection |
| 🧠 **Memory System** | Daily logs, learnings, and long-term memory across sessions |
| ⚡ **Skill System** | Modular skills — browse web, shell commands, phone calls, reports |
| 🤖 **Sub-Agents** | Spawn specialized agents for recurring tasks |
| 📊 **Health Monitoring** | CPU, RAM, disk, uptime — all visible from dashboard and Telegram |
| 🔧 **Smart Model Router** | Local LLM for simple tasks, Claude for complex ones |
| 📞 **Voice Calls** | Real Telegram voice calls for critical alerts and reminders |
| 🔍 **Web Search** | Native Claude web search (SDK brain); DuckDuckGo fallback for the CLI brain |
| 🔗 **Link Reader** | Auto-extracts page content from URLs in messages |
| ⏰ **Smart Reminders** | Set by chat or dashboard — message, voice call, or both; full management UI |

## 🏗️ Architecture

```
              ┌───────────────────────────┐
              │    Claude Agent SDK       │  ← The Brain (pluggable)
              │  Sonnet / Opus, streaming │     `claude -p` CLI fallback
              │  native tools + MCP       │
              └────────────┬──────────────┘
                           │
┌─────────────┐     ┌──────┴─────────┐     ┌──────────────┐
│  Telegram   │────▶│    Gateway     │────▶│  Local LLM   │
│  (channel)  │◀────│   (FastAPI)    │◀────│  (Optional)  │
└─────────────┘     └──────┬─────────┘     └──────────────┘
                           │                ┌──────────────────────┐
                    ┌──────┴───────┐        │ External MCP servers │
                    │  Dashboard   │────────│ Home Assistant, ...  │
                    │  (channel)   │        │ + Store to add more  │
                    └──────────────┘        └──────────────────────┘
```

| Component | Technology |
|-----------|-----------|
| **Brain** | Claude Agent SDK — Sonnet & Opus, streaming, tools (CLI fallback, pluggable via `src/brains/`) |
| **Gateway** | Python 3.13, FastAPI, Uvicorn |
| **Telegram** | python-telegram-bot |
| **Local LLM** | Ollama, LM Studio, or any OpenAI-compatible endpoint (optional) |
| **Dashboard** | React, Vite, Tailwind CSS, Lucide Icons |
| **Database** | SQLite (memories, reminders, routines, heartbeat log, permissions, stats) |
| **Voice** | pyrofork + py-tgcalls + FFmpeg for Telegram calls · Whisper (Groq or local) for transcription · edge-tts for speech |

### Smart Model Router

KOVO intelligently routes messages to the right model:

| Complexity | Routed To | Use Case |
|------------|-----------|----------|
| **Simple** | Claude Sonnet | Quick Q&A, greetings, status checks |
| **Medium** | Claude Sonnet | Most tasks, code, analysis |
| **Complex** | Claude Opus | Deep reasoning, architecture, planning |

> Local LLM (Ollama) is used exclusively for heartbeat health summaries — never in the message routing path. Live Call turns use a fast model to keep conversation latency down.

## 🖥️ Dashboard

The built-in web dashboard gives you full visibility into KOVO's state:

Redesigned in v2.1 with a cool slate design system, per-domain accent colors, and a
three-section navigation (Agent · Capabilities · System). v3.0 adds the **Routines**
and **Add-ons** pages. Login is Telegram-approved: the dashboard shows a code, your
bot asks you to approve it — with an optional owner-allowlisted **Google sign-in**
once configured.

| Section | What It Shows |
|---------|---------------|
| 📡 **Overview (Mission Control)** | Live activity feed, "Kovo is working on…" indicator, 24h CPU/RAM/disk sparklines, quick-chat, routines + reminders + integrations + security widgets |
| 💬 **Chat** | Talk to KOVO from the browser with live streaming replies (WebSocket) |
| ⏰ **Routines** | Create and manage recurring autonomous tasks — schedule presets or custom cron, enable/disable, Run now, per-run history |
| 🧠 **Memory** | Browse daily logs and workspace files |
| ⚡ **Skills & Agents** | The main agent, full skills management, sub-agents, and the pending queue of skills KOVO proposes to learn |
| 🔧 **Tools** | All registered tools with status and install commands |
| 🔌 **Integrations** | MCP servers with connection tests + **Store**: curated catalog and live search of the official MCP registry |
| 🧩 **Add-ons** | Guided companion setup — Tailscale, Google Workspace, Ollama, Home Assistant — with live status detection and show-commands-first installs |
| 💓 **Heartbeat** | Scheduled job status, health reports, and full reminders management |
| 🛡️ **Security** | Latest audit results, history, run/reset from UI |
| 📜 **Logs** | Live gateway logs |
| ⚙️ **Settings** | YAML config editor + environment variables |
| 🧙 **Setup Wizard** | First-time guided configuration with step-by-step credential guides, finishing at the Add-ons page |

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
- **Add-ons** — optional guided setup for Tailscale, Google Workspace, Ollama, and Home Assistant

Credentials are saved to `config/.env` on your machine — never transmitted.

> **Prefer manual setup?** Copy `config/.env.template` to `config/.env` and fill in your tokens, then restart the service.

### v3.0 Configuration Highlights

```yaml
backup:
  offsite:
    enabled: true        # nightly backup upload to your Google Drive
    keep: 7              # how many off-site backups to retain

voice:
  reply_in_kind: true    # voice message in → voice note reply (default on)

experimental:
  live_call: false       # 🧪 opt in to real-time Live Call conversations
```

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

KOVO uses a persistent reply keyboard with emoji buttons, and since v3.0 registers the bot command menu — type `/` and commands autocomplete:

| Button | Command | What It Does |
|--------|---------|--------------|
| 📡 Status | `/status` | Service status — tools, skills, agents |
| 🖥️ Health | `/health` | CPU %, RAM in GB, disk usage |
| 🧠 Memory | `/memory` | Today's session log |
| 💾 Storage | `/storage` | File storage usage with gauge |
| 📚 Skills | `/skills` | List all loaded skills |
| 🔧 Tools | `/tools` | Tool registry with status |
| 📞 Live Call | `/livecall` | Start a live voice conversation (🧪 experimental, off by default) |

Plus: `/agents`, `/permissions`, `/purge`, `/reminders`, `/remind cancel <id>`, `/search`, `/call`, `/db`, and natural language for everything else — including "remind me tomorrow at 9" (one-time) and "check my email every Sunday" (a Routine).

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

And since v3.0, KOVO **grows its own skill library**: when a topic keeps recurring with no matching skill, it drafts one and asks for your approval — in Telegram ("🎓 Learn it" / "Not now") or from the dashboard pending queue with a full preview. Approved skills hot-reload immediately and carry a 🎓 learned badge.

## 🛡️ Security

KOVO includes built-in security features:

- **Owner approval everywhere** — learned skills, Kovo-proposed routines, and sub-agents never activate without your explicit approval
- **Token masking** — all API keys masked in log output
- **`.env` validation** — warns if required vars are missing; starts in dashboard-only mode
- **File permissions** — `.env`, credentials, and DB set to `chmod 600`
- **Shell blocklist** — dangerous commands blocked or require confirmation
- **Security audits** — automated port scan, user check, ClamAV, chkrootkit
- **Pre-push git hook** — blocks personal data, `.env`, credentials, and database files from being committed
- **Personal data isolation** — repo ships `.template` files only; live workspace files are gitignored
- **Claude Code sandbox** — pre-approved command allowlist, runtime approval via Telegram
- **Show-before-run installs** — the Add-ons page displays the exact commands before executing anything
- **Google sign-in allowlist** — optional dashboard login restricted to one owner account; the button stays hidden until fully configured
- **Shell metachar blocking** — `;|&$\`><(){}!` blocked in all API command endpoints
- **Env key whitelist** — dashboard can only write approved KOVO configuration keys
- **Backup validation** — tar archives checked for path traversal and source code injection before extraction
- **Off-site backups to your own Drive** — nightly, pruned, alert on failure; your data never touches third-party storage you don't control
- **Reminder date validation** — rejects invalid dates that would fire immediately

## 📁 Project Structure

```
<KOVO_DIR>/              # /opt/kovo (Linux) or ~/.kovo (macOS)
├── config/          # .env, settings.yaml, credentials
├── data/            # SQLite DB, security audit data, temp files
├── scripts/         # Helper scripts
├── src/
│   ├── agents/      # Main agent + sub-agent runner + native toolkit
│   ├── dashboard/   # FastAPI API + React frontend
│   ├── gateway/     # FastAPI app, startup, config
│   ├── heartbeat/   # Scheduled tasks (APScheduler)
│   ├── memory/      # Memory system (MD + SQLite)
│   ├── onboarding/  # First-run guided setup
│   ├── router/      # Smart model router (local LLM / Claude)
│   ├── skills/      # Skill registry + loader
│   ├── telegram/    # Bot, commands, formatting
│   ├── tools/       # Tool registry (routines, live call, backups, browser, etc.)
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
| **AI connection** | Claude Agent SDK (streaming, tools, MCP; CLI fallback) | Direct API calls (OpenAI, Anthropic, etc.) |
| **Billing** | Flat rate — Claude Max subscription (~$100-200/mo) | Pay per token — costs vary with usage |
| **Models** | Claude Sonnet & Opus (pluggable brains — more backends addable) | Any provider (OpenAI, Anthropic, Groq, local) |
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
<summary><strong>Live Call does nothing</strong></summary>

- Live Call is 🧪 experimental and **off by default** — set `experimental.live_call: true` in `settings.yaml` and restart
- It needs the voice-call accounts configured (see the Setup Wizard's Voice Calls step)
- A `GROQ_API_KEY` is strongly recommended — without it, transcription falls back to slower local CPU Whisper and turns feel sluggish
- Expect ~3–6 s per turn in v1 — it's a composed pipeline, not a realtime voice API
</details>

<details>
<summary><strong>Off-site backup not uploading</strong></summary>

- Requires Google Workspace configured (Drive scope) — use the Add-ons page or `/auth_google` in Telegram
- Check `backup.offsite.enabled: true` in `settings.yaml`
- Test manually: `venv/bin/python -m src.tools.offsite_backup`
- On failure KOVO alerts you in Telegram; on success it's silent by design
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