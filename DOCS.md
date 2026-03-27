# Kovo — User Documentation

**Version**: 0.3
**Last Updated**: 2026-03-24
**Platform**: Ubuntu 25.10, Python 3.13, Claude Max subscription

---

## Table of Contents

1. [What Is Kovo?](#1-what-is-kovo)
2. [Architecture Overview](#2-architecture-overview)
3. [Prerequisites](#3-prerequisites)
4. [Installation Guide](#4-installation-guide)
5. [Authentication & Secrets](#5-authentication--secrets)
6. [Telegram Commands](#6-telegram-commands)
   - [6b. Telegram Interface](#6b-telegram-interface)
7. [Talking to the Agent](#7-talking-to-the-agent)
8. [Agent Personality (SOUL.md)](#8-agent-personality-soulmd)
9. [Memory System](#9-memory-system)
10. [Skills](#10-skills)
11. [Voice Calls](#11-voice-calls)
12. [Google Workspace](#12-google-workspace)
13. [GitHub Integration](#13-github-integration)
14. [Dashboard](#14-dashboard)
15. [Replicating for Friends](#15-replicating-for-friends)
16. [Heartbeat System](#16-heartbeat-system)
17. [Backup & Recovery](#17-backup--recovery)
18. [First-Run Onboarding](#18-first-run-onboarding)
19. [Storage Management](#19-storage-management)
20. [Permission System](#20-permission-system)
21. [Troubleshooting](#21-troubleshooting)
22. [Changelog](#22-changelog)
23. [Security](#23-security)
24. [Security Audit](#24-security-audit)
25. [Migration: KOVO → Kovo](#25-migration-kovo--kovo)

---

## 1. What Is Kovo?

Kovo is a self-hosted personal AI assistant that lives on your own server and talks to you through Telegram. It uses Claude (via your Max subscription) for intelligence and runs on a small Ubuntu VM.

**What it can do:**
- Answer questions and have conversations via Telegram or a web dashboard
- Run shell commands and manage your server (installs, services, monitoring)
- Browse the web, scrape pages, take screenshots
- Send and read Google Docs, Drive, and Gmail
- Place Telegram voice calls with TTS audio for urgent alerts
- Transcribe voice messages you send it
- Monitor server health and alert you proactively
- Learn new skills and create sub-agents for specialist tasks

**What it costs:**
- ~$100–200/month Claude Max subscription (covers all Claude usage)
- Everything else (Ollama, edge-tts, Playwright, Whisper) is free
- VM running cost depends on your setup (Unraid, VPS, etc.)

---

## 2. Architecture Overview

```
You (Telegram)  ←→  Web Dashboard
        │                   │
        ▼                   ▼
   Gateway (FastAPI, port 8080)
        │
        ├── Kovo — the ONE agent you talk to
        │     ├── Smart context loading (only loads what each message needs)
        │     ├── Has access to all tools
        │     └── Delegates to sub-agents when created
        │
        ├── Smart Router
        │     ├── Claude Sonnet → medium tasks
        │     └── Claude Opus  → complex reasoning
        │
        ├── Tool Registry (workspace/TOOLS.md)
        ├── Memory System (Markdown + SQLite)
        ├── Skills System (SKILL.md format)
        ├── Heartbeat Scheduler (APScheduler)
        └── Storage Manager (GC, disk monitoring)
```

**Key design choice:** One agent handles everything. Kovo only loads the context relevant to your message — not everything every time. This saves 60–90% of system prompt tokens on routine messages. Sub-agents are created only when you explicitly approve them.

**Ollama** (on a NUC at `<OLLAMA-HOST>:11434`) handles heartbeat health checks only. All your messages go to Claude.

---

## 3. Prerequisites

| Item | Requirement |
|------|-------------|
| Server | Ubuntu 25.10 (Questing) — other versions untested |
| RAM | 8GB minimum |
| Disk | 50GB minimum |
| Python | 3.13.x — do **not** install 3.12 |
| Node.js | 22+ via NodeSource — do **not** use Ubuntu's `npm` package |
| Claude | Max subscription ($100/month) — needed for `claude` CLI |
| Telegram | A bot token (from @BotFather) and your Telegram user ID |
| Network | Outbound internet access for Claude, Telegram, Ollama |

**Optional integrations:**
- Groq API key — for fast cloud Whisper transcription
- Telegram API credentials (`api_id` + `api_hash`) — for voice calls
- Google OAuth credentials — for Docs/Drive/Gmail
- GitHub personal access token — for repo management

---

## 4. Installation Guide

### Step 1: Provision Ubuntu 25.10 VM

Create a VM with 8GB RAM, 50GB disk. Ubuntu 25.10 (Questing) only.

### Step 2: Run bootstrap

```bash
wget -O bootstrap.sh https://raw.githubusercontent.com/Ava-AgentOne/kovo/main/bootstrap.sh
bash bootstrap.sh
```

Bootstrap v4.0 handles everything automatically:
- System packages, Redis, Node.js 22, Claude Code CLI, security tools
- **Clones source code from GitHub** (identical code for every install)
- Python venv with all dependencies installed from `requirements.txt`
- Dashboard frontend built from source
- Playwright + Chromium
- All directory structure including `data/` subdirs
- Workspace files with onboarding placeholders
- Claude Code permissions file (prevents runtime prompts)
- Systemd service, logrotate, sudo NOPASSWD
- File permissions (chmod 600/700 on secrets)

### Step 3: Authenticate Claude Code

```bash
claude setup-token
```

Follow the URL it prints, authorize in your browser, paste the token back. Then save it:

```bash
echo 'export CLAUDE_CODE_OAUTH_TOKEN=YOUR_TOKEN_HERE' >> ~/.bashrc
source ~/.bashrc
```

Also set it in your `.env` file (Step 4 below).

### Step 4: Configure secrets

```bash
cp /opt/kovo/config/.env.template /opt/kovo/config/.env
nano /opt/kovo/config/.env
```

Fill in at minimum:
- `TELEGRAM_BOT_TOKEN` — from @BotFather
- `OWNER_TELEGRAM_ID` — your Telegram user ID (find via @userinfobot)
- `CLAUDE_CODE_OAUTH_TOKEN` — from Step 3

Everything else is optional and can be configured later via Telegram commands.

### Step 5: Start the service

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now kovo
sudo systemctl status kovo
```

### Step 6: Complete onboarding via Telegram

Send any message to your bot on Telegram. **You don't need to manually edit SOUL.md, USER.md, or IDENTITY.md** — the agent will run a 2-minute guided interview and write these files for you automatically.

See [Section 18](#18-first-run-onboarding) for the full onboarding flow.

---

## 5. Authentication & Secrets

All secrets live in `/opt/kovo/config/.env`. Never commit this file.

| Variable | Description | Required |
|----------|-------------|----------|
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather | Yes |
| `OWNER_TELEGRAM_ID` | Your Telegram user ID | Yes |
| `CLAUDE_CODE_OAUTH_TOKEN` | Claude Max auth token | Yes |
| `GROQ_API_KEY` | Groq Whisper transcription | Optional |
| `TELEGRAM_API_ID` | From my.telegram.org — for voice calls | Optional |
| `TELEGRAM_API_HASH` | From my.telegram.org — for voice calls | Optional |
| `GITHUB_TOKEN` | Personal access token for GitHub | Optional |
| `GOOGLE_CREDENTIALS_PATH` | Path to OAuth2 credentials JSON | Optional |

**Add credentials later via Telegram commands:**
- Google: `/auth_google`
- GitHub: `/auth_github`
- Voice calls: `/reauth_caller +PHONENUMBER`

---

## 6. Telegram Commands

> **Quick access:** A persistent keyboard with 6 buttons (📡 Status, 🖥 Health, 🧠 Memory, 💾 Storage, 📚 Skills, 🔧 Tools) stays visible at the bottom of every chat. Tap instead of typing. See [Section 6b](#6b-telegram-interface) for the full UI spec.

### Core

| Command | Description |
|---------|-------------|
| `/start` | Show all available commands |
| `/status` | System status (tools, agents, heartbeat) |
| `/health` | Live health check (CPU, RAM, disk) |
| `/clear` | Clear session history — start fresh |
| `/model <sonnet\|opus>` | Force a specific model for next message |

### Memory & Skills

| Command | Description |
|---------|-------------|
| `/memory` | Show today's activity log |
| `/memory extracted` | Show memories auto-extracted in the last 24 hours |
| `/memory search <query>` | Search all memories (markdown + database) |
| `/memory stats` | Show conversation statistics |
| `/flush` | Extract today's learnings into MEMORY.md + SQLite (Claude Sonnet, deduped) |
| `/flush <text>` | Write specific text directly to MEMORY.md |
| `/skills` | List loaded skills |
| `/newskill` | Create a new skill interactively |

### Database

| Command | Description |
|---------|-------------|
| `/db` | Show database tables and sizes |
| `/db query <question>` | Ask a question about stored data in plain English |

### Storage

| Command | Description |
|---------|-------------|
| `/storage` | Disk report with progress bar + per-directory breakdown |
| `/purge all` | Review old files — tap **Confirm** / **Cancel** inline buttons |
| `/purge photos` | Review old photos only (older than 30 days) |
| `/purge documents` | Review old documents only |
| `/purge images` | Review old images only |
| `/purge confirm` | Text fallback to execute a pending purge |

### Permissions

| Command | Description |
|---------|-------------|
| `/permissions` | View allowlist; shows **Approve** / **Deny** buttons if pending |
| `/approve` | Text fallback — grant a pending permission |
| `/deny` | Text fallback — reject a pending permission |

### Tools & Agents

| Command | Description |
|---------|-------------|
| `/tools` | Tool registry with install/config status |
| `/agents` | List sub-agents |

### Phone

| Command | Description |
|---------|-------------|
| `/call <text>` | Place a voice call with TTS audio |
| `/reauth_caller +PHONE` | Re-authenticate the caller (userbot) account |

### Integrations

| Command | Description |
|---------|-------------|
| `/auth_google` | Start Google OAuth flow |
| `/auth_github` | Verify GitHub token |
| `/search <query>` | Quick DuckDuckGo web search |

---

## 6b. Telegram Interface

### Persistent Keyboard

Every agent reply includes a 6-button reply keyboard that stays visible at the bottom of the chat:

```
[ 📡 Status  ]  [ 🖥 Health  ]
[ 🧠 Memory  ]  [ 💾 Storage ]
[ 📚 Skills  ]  [ 🔧 Tools   ]
```

Buttons use emoji labels (no `/`). Tapping one sends the label as a text message which the bot intercepts and routes to the appropriate command. You can still type free-form messages normally.

### Inline Buttons

Confirmation prompts use inline buttons that appear under the message and disappear after tapping:

| Prompt | Buttons |
|---|---|
| Permission request | ✅ Approve / ❌ Deny |
| `/purge` review | 🗑 Yes, delete / Cancel |
| Sub-agent suggestion | 👍 Create it / Not now |

Tapping edits the original message to show the result — keeps the chat clean.

### Formatted Responses

Command responses are formatted for mobile (≤35 chars/line). Key visual elements:

**`/health`** — live psutil metrics with `▓░` progress bars:
```
🖥 Health Report

CPU   ▓▓░░░░░░░░  12%
RAM   ▓▓▓▓▓░░░░░  3.6 / 8 GB
Disk  ▓▓▓▓▓▓▓░░░  67%

✅ All systems normal
⏱ Uptime: 14d 6h
🕐 Next check: 30 min
```

**`/storage`** — disk bar + compact file list (no policy tags):
```
📊 Storage Report

💾 ▓▓▓░░░░░░░░░ 44%
11.6 / 30 GB (16.7 GB free)

📁 audio        2 MB
📁 photos     132 KB
...

🕐 Last purge: 3h ago
```

**`/memory`** — parsed activity bullets:
```
🧠 Today's Memory

📅 Mar 24, 2026

• 08:00 Morning briefing sent
• 09:15 Health check — all normal
...

📝 5 entries | /flush to save
```

Progress bar thresholds:
- CPU > 80% = ⚠️, > 95% = 🚨
- RAM > 80% = ⚠️
- Disk > 85% = ⚠️, > 95% = 🚨

---

## 7. Talking to the Agent

Just send a message. No commands needed for most things:

```
"What's the disk usage on the server?"
"Summarize my emails from today"
"Check if the kovo service is running"
"Write a Python script to parse this CSV"
"Search for the best way to configure nginx rate limiting"
```

**Voice messages:** Send a voice note — Kovo transcribes it with Whisper and responds in text (and voice if you used `/call`).

**Photos:** Send a photo with or without a caption. Kovo uses Claude Vision to analyze it.

**Documents:** Send a PDF, DOCX, or text file. Kovo reads and summarizes it, or does whatever your caption asks.

**Quoting:** Reply to any message to give it context. Kovo sees the quoted message.

---

## 8. Agent Personality (SOUL.md)

After onboarding, Kovo's personality lives in `workspace/SOUL.md`. You can read and edit it directly:

```bash
cat /opt/kovo/workspace/SOUL.md
nano /opt/kovo/workspace/SOUL.md
```

No restart needed — Kovo reads SOUL.md on every message.

**Related files:**
- `workspace/USER.md` — your profile (name, city, timezone, preferences)
- `workspace/IDENTITY.md` — agent name, style, creation date
- `workspace/MEMORY.md` — long-term curated memory

To re-run onboarding on an existing install, add `## UNCONFIGURED` anywhere in SOUL.md. The next message triggers the interview again.

---

## 9. Memory System

Kovo has three layers of memory that work together automatically:

**Layer 1 — Markdown files (human-readable)**

- `workspace/MEMORY.md` — long-term memory, organized by category: Preferences, Decisions, Facts, Projects, Action Items. You can read and edit this file directly.
- `workspace/memory/YYYY-MM-DD.md` — daily conversation logs. Auto-created, sent to the morning briefing, archived after 30 days.
- `workspace/memory/archive/` — old daily logs and archived memories.

**Layer 2 — SQLite database (queryable)**

`data/kovo.db` stores the same memories in a structured format, plus heartbeat history, permission logs, and conversation stats. You can query it in plain English:

```
/db query how many memories do I have about projects?
/db query show me the last 10 permission approvals
/db query what was the server health last week?
```

Kovo can also create custom tables on demand when you ask it to track something specific.

**Layer 3 — Auto-extraction (daily, hands-off)**

Once per day (at 11 PM), Kovo reads through the day's conversations and picks out important facts — preferences you mentioned, decisions you made, project details, things to remember. No action needed from you.

- One Claude Sonnet call per day (capped at ~4000 tokens of conversation)
- Duplicates are filtered automatically (no LLM call for dedup)
- Stored in both MEMORY.md and the SQLite database
- Use `/flush` to trigger it manually at any time

**Smart context loading**

Kovo only loads the memory relevant to your message, not everything. Sending "hi" loads ~300 tokens (SOUL + USER + IDENTITY). Asking "what did we decide about auth?" loads MEMORY.md. Asking "check disk usage" loads HEARTBEAT.md. This saves 60–90% of tokens on routine messages.

**Commands:**
- `/memory` — today's log
- `/memory extracted` — last memories auto-extracted (last 24h)
- `/memory search <query>` — search across markdown files and database
- `/memory stats` — conversation stats and memory counts
- `/flush` — extract today's learnings (or `/flush <text>` to write directly)
- `/db` — show database schema
- `/db query <question>` — natural language database query

---

## 10. Skills

Skills are procedures the agent knows how to follow. They live in `workspace/skills/` as SKILL.md files.

**Create a skill:**
```
/newskill backup | Manage workspace backups | backup,archive | Run scripts/backup.sh to create a workspace backup.
```

Format: `name | description | trigger1,trigger2 | skill body`

**View skills:**
```
/skills
```

The best-matching skill is loaded into the system prompt when its trigger keywords appear in your message. Only one skill loads per message (the one with the most trigger hits), saving tokens.

**Built-in skill (ships with every install):**

- **report-builder** — generates polished HTML reports from any structured data.
  Dark/light mode, animated charts, score rings, sparklines, responsive layout, email-ready.
  Ask: *"generate a health report"* or *"build me a weekly summary report"*
  Output: `/opt/kovo/data/documents/Report_Name_YYYYMMDD.html`

---

## 11. Voice Calls

Kovo can place real Telegram voice calls using a second Telegram account (userbot) with TTS audio.

**Setup:**
1. Get a second Telegram account (spare number or eSIM)
2. Get API credentials: https://my.telegram.org → API development tools
3. Set `TELEGRAM_API_ID` and `TELEGRAM_API_HASH` in `.env`
4. Run `/reauth_caller +YOURPHONENUMBER` in Telegram
5. Enter the OTP when prompted

**Usage:**
```
/call Hey the owner, the disk is almost full!
```

Or send any message marked as urgent — the agent decides when to call.

**Fallback:** If the call isn't answered in 30 seconds, Kovo sends a voice message instead.

**TTS voice:** Configured in `settings.yaml` under `telegram_call.tts.voice`. Defaults to `en-US-AvaMultilingualNeural` (edge-tts, free Microsoft voice). Supports all edge-tts voices including Arabic.

**Prepaid SIM reminder:** Kovo alerts you every 80 days to top up the prepaid SIM — UAE prepaid SIMs expire after 90 days without activity.

---

## 12. Google Workspace

**Setup:**
1. Create a Google Cloud project and OAuth2 credentials
2. Download the credentials JSON to `/opt/kovo/config/google-credentials.json`
3. Run `/auth_google` in Telegram
4. Follow the URL, authorize, paste the code back

**Capabilities (once authenticated):**
- Create and edit Google Docs
- Upload/download files from Google Drive
- Send and read Gmail
- Read Google Calendar events

---

## 13. GitHub Integration

**Setup:**
1. Create a personal access token at https://github.com/settings/tokens (scopes: `repo`, `read:user`)
2. Add `GITHUB_TOKEN=your_token` to `.env`
3. Run `/auth_github` to verify

**Capabilities:**
- Browse repos, issues, and pull requests
- Create issues, comment, close PRs
- Read and write files in repos
- Search code

---

## 14. Dashboard

The web dashboard runs at `http://your-server:8080/dashboard`.

**Pages:**
- **Overview** — agent + sub-agents status, today's activity
- **Chat** — full chat interface with Kovo (same as Telegram, backup channel)
- **Tools** — tool registry with install/config status
- **Agents** — sub-agents with SOUL preview
- **Memory** — browse/edit workspace files
- **Skills** — skill registry
- **Heartbeat** — schedule and history
- **Logs** — real-time log viewer

**Build the frontend** (if not already built):
```bash
cd /opt/kovo/src/dashboard/frontend
npm install && npm run build
```

---

## 15. Replicating for Friends

To give a friend their own Kovo instance:

**What they need:**
- A fresh Ubuntu 25.10 VM (8GB RAM, 50GB disk)
- A Claude Max subscription
- A Telegram bot token (from @BotFather)
- Their Telegram user ID

**Steps:**
1. Run bootstrap (clones identical source from GitHub automatically):
   ```bash
   wget -O bootstrap.sh https://raw.githubusercontent.com/Ava-AgentOne/kovo/main/bootstrap.sh
   bash bootstrap.sh
   ```
2. Authenticate Claude: `claude setup-token`
3. Configure `.env` with their credentials
4. Start service: `sudo systemctl enable --now kovo`
5. **Send a message on Telegram** — the agent runs a 2-minute setup interview to configure their name, profile, and personality. No manual file editing or code generation needed.

Every friend gets the **identical codebase, dashboard, and logo** as you — no variation between installs.

Memory features (auto-extraction, SQLite, smart context loading) activate automatically after first use. No extra configuration needed.

**Migrating from OpenClaw:**
```bash
/opt/kovo/scripts/migrate_openclaw.sh /path/to/openclaw/workspace
```

This copies SOUL.md, USER.md, MEMORY.md, skills, and memory files. Review TOOLS.md afterward to update paths.

---

## 16. Heartbeat System

Kovo monitors itself and reports proactively.

| Schedule | What happens |
|----------|-------------|
| Every 30 min | Quick health check via Ollama — alerts if CPU/RAM/disk thresholds exceeded |
| Every 6 hours | Full health report via Claude — summarized and sent to Telegram |
| Every 6 hours | Auto-purge old tmp/audio/screenshot files silently |
| Every 6 hours | Disk check — alert if free space drops below 15% |
| Every morning 8 AM | Good morning briefing with system status and yesterday's activity |
| Daily 11 PM | Auto-memory extraction — picks out learnings from today's conversations and stores them in MEMORY.md + SQLite |
| Sunday 3 AM | Weekly storage review — asks if you want to clean old photos/documents |
| Sunday 3:30 AM | Memory budget check — archives MEMORY.md if it exceeds 500 lines |
| Sunday 7 AM | Full security audit — network, packages, users, files, processes, malware scan |
| Every 80 days | Reminder to top up prepaid SIM for voice calls |

**Thresholds (quick check):**
- CPU 5-min load average > 4.0 → alert
- RAM usage > 80% → alert
- Disk usage > 85% → alert

**Configure in:** `workspace/HEARTBEAT.md` (edit the checklist directly)

---

## 17. Backup & Recovery

**Manual backup:**
```bash
/opt/kovo/scripts/backup.sh
```

Creates `data/backups/workspace_YYYYMMDD.tar.gz`. Keeps 30 days of backups.

**Automatic:** Set up a cron or have the agent schedule it.

**What's backed up:** Everything in `workspace/` — SOUL.md, memory, skills, agents, checklists, docs.

**Restore:**
```bash
tar xzf /opt/kovo/data/backups/workspace_YYYYMMDD.tar.gz -C /opt/kovo
```

**Service logs:**
```bash
sudo journalctl -fu kovo          # follow live
sudo journalctl -u kovo --since today
tail -f /opt/kovo/logs/gateway.log
```

---

## 18. First-Run Onboarding

When Kovo is installed fresh (via bootstrap.sh), the very first message you send on Telegram starts a guided setup interview instead of normal operation.

**What triggers it:** `workspace/SOUL.md` contains the line `## UNCONFIGURED`. Bootstrap sets this automatically.

### The Interview

Takes about 2 minutes. The agent guides you through five steps:

**Step 1 — Pick a name**
What do you want to call your agent? Jarvis, Friday, Nova, or anything you like.

**Step 2 — Your profile**
Answer these (all at once or one by one):
- Your name
- City and country
- Languages you speak
- What you do (job, hobby, student)
- Email address (for Google integration — say "skip" to skip)

**Step 3 — Personality**
Pick a style:
- 🎯 **Professional** — clean, concise, no fluff
- 😊 **Friendly** — casual, warm, like texting a smart friend
- 😏 **Sarcastic** — gets things done but with humor
- ⚡ **Minimal** — just answers, no small talk
- 🎨 **Custom** — describe your own

Also tell it:
- Emoji usage: lots / sometimes / never
- Proactive mode: should it suggest things without being asked?

**Step 4 — Confirm**
Agent shows a summary. Say "yes" to lock it in, or describe what to change.

**Step 5 — Generate**
Agent writes four files using your answers:
- `workspace/SOUL.md` — personality, values, style
- `workspace/USER.md` — your profile
- `workspace/IDENTITY.md` — agent name, style, creation date
- `workspace/MEMORY.md` — initial memory entry

After this, normal operation starts immediately. No restart needed.

### Restart Resilience

Onboarding state is saved in `workspace/.onboarding_state.json`. If the service restarts mid-interview, the conversation picks up where it left off. Use `/skip` at any time to jump straight to generation with sensible defaults.

### Sub-Agent Onboarding

When Kovo recommends creating a sub-agent and you approve, a lighter 3-question flow runs:
1. Name for the sub-agent
2. Personality (inherit from Kovo, Professional, or Custom)
3. Any special instructions

The sub-agent is created at `workspace/agents/{name}/SOUL.md`.

### Re-running Onboarding

To reset the agent's identity on an existing install, add `## UNCONFIGURED` to `workspace/SOUL.md`. The next message triggers the interview again.

---

## 19. Storage Management

Kovo automatically manages disk space with a three-tier system.

### Tier 1 — Auto-Purge (no approval needed)

Runs silently every 6 hours. Only notifies you if it freed more than 10MB.

| Directory | What's kept | What's deleted |
|-----------|-------------|----------------|
| `data/tmp/` | — | Everything older than 1 day |
| `data/audio/` | — | Voice files older than 7 days |
| `data/screenshots/` | — | Browser screenshots older than 7 days |
| `src/**/__pycache__/` | — | All compiled Python bytecode |

### Tier 2 — Ask Before Purge

Kovo scans these directories every Sunday at 3 AM. If it finds old files, it sends you a message listing what it found and asking for approval. Nothing is deleted until you reply.

| Directory | Old = older than |
|-----------|-----------------|
| `data/photos/` | 30 days |
| `data/documents/` | 30 days |
| `data/images/` | 30 days |

### Tier 3 — Never Auto-Delete

| What | How it's managed |
|------|-----------------|
| `workspace/memory/` | Archived (not deleted) after 30 days |
| `workspace/MEMORY.md` | Never touched |
| `data/backups/` | Kept for 30 days, then deleted by `backup.sh` |

### Commands

**`/storage`** — full disk report:
```
📊 Storage Report

Disk: 12.4GB / 50GB (25% used, 37.6GB free)

📁 audio           8MB   (auto-purge: 7 days)
📁 photos        142MB   (review: 30 days)
📁 documents      23MB   (review: 30 days)
📁 images         15MB   (review: 30 days)
📁 screenshots     2MB   (auto-purge: 7 days)
📁 tmp             0MB   (auto-purge: 1 day)
📁 backups        89MB   (keep: 30 days)
📁 logs            4MB   (logrotate: 7 days)

Last auto-purge: 3h ago
```

**`/purge all`** — review all old Tier 2 files (photos + documents + images), get a confirmation prompt, then execute with `/purge confirm`.

**`/purge photos`** / **`/purge documents`** / **`/purge images`** — same but for a single directory.

Sending any other message after `/purge` cancels the pending operation.

### Low Disk Alerts

If free space drops below 15%, Kovo sends:
```
⚠️ Low Disk Space!

Only 4.2GB free (8.4%)

Top space users:
  📁 audio/  1.2GB
  📁 photos/  890MB
  📁 venv/   1.5GB (system)

I can auto-purge audio and screenshots to free ~1.2GB.
Run /purge all to also clean old photos/documents.
Or run /storage for the full report.
```

---

## 20. Permission System

Claude Code runs in a sandbox that blocks commands it hasn't been explicitly authorized to run. Kovo handles this automatically.

### Build-Time Permissions

Bootstrap v3.0 pre-creates `/opt/kovo/.claude/settings.local.json` with 60+ pre-approved entries. This means Claude Code never asks permission during the initial build or normal operation.

Pre-approved commands include: all common Unix tools (`ls`, `cat`, `grep`, `find`, `sed`, `awk`, `tar`, `curl`, `wget`), system operations (`apt`, `chmod`, `chown`, `sudo`, `systemctl`, `docker`, `kill`), Python tools (`pip`, `playwright`, `python`), and file editing (`Edit(*)`).

### Runtime Self-Updating

If the agent tries to run a command that isn't in the allowlist:

1. The block is detected in the claude CLI output
2. Kovo sends you a Telegram message:
   ```
   🔒 Permission Request

   I tried to run a command but it's blocked by my sandbox:

   Command: docker compose up -d
   Permission needed: Bash(docker *)

   This would permanently allow me to use docker commands.

   Reply /approve to grant or /deny to reject.
   ```
3. **`/approve`** — adds the pattern to `settings.local.json` and retries the original task
4. **`/deny`** — clears the request and Kovo finds another way

If the retry hits another blocked command, a second request is sent. The process chains until the task completes or you deny a step.

### Viewing Permissions

**`/permissions`** — shows the full allowlist with count:
```
🔑 Claude Code Permissions (61 entries)

`Bash(apt *)`, `Bash(docker *)`, `Bash(curl *)`, ...

These are commands I can run without asking.
New ones are added when you approve /approve requests.
```

### Security

- Only the Telegram user ID in `OWNER_TELEGRAM_ID` can approve permissions
- Every approval is logged to the daily memory file
- Patterns follow Claude Code sandbox syntax: `Bash(command *)` or `Edit(*)`
- The file is at `/opt/kovo/.claude/settings.local.json` — you can edit it manually

---

## 21. Troubleshooting

### Service won't start

```bash
sudo journalctl -u kovo -n 50
sudo systemctl status kovo
```

Common causes:
- Missing `.env` file — copy from `.env.template` and fill in credentials
- Python venv not built — run `bash bootstrap.sh` again
- Port 8080 already in use — `sudo lsof -i :8080`

### Bot not responding

1. Check service is running: `sudo systemctl status kovo`
2. Check logs: `tail -f /opt/kovo/logs/gateway.log`
3. Verify bot token: `curl https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getMe`
4. Make sure your Telegram user ID is in `OWNER_TELEGRAM_ID`

### "Claude not found" or auth errors

```bash
which claude          # should return /usr/local/bin/claude
claude --version
claude setup-token    # re-authenticate
```

Make sure `CLAUDE_CODE_OAUTH_TOKEN` is set in `.env`.

### Ollama heartbeats failing

This is non-fatal — heartbeat reports will be skipped but the bot still works.

```bash
curl http://<OLLAMA-HOST>:11434/api/version
```

If unreachable, Ollama is offline or the NUC is down. Kovo will send a warning and skip the summary.

### Voice transcription not working

Check `GROQ_API_KEY` in `.env`. If missing, Kovo falls back to local Whisper (slower but free).

### Onboarding not triggering

Check that `## UNCONFIGURED` is in `workspace/SOUL.md`:
```bash
grep UNCONFIGURED /opt/kovo/workspace/SOUL.md
```

If not present, add it manually, then send a message.

### Disk full

```bash
df -h /opt/kovo
```

Quick cleanup:
```bash
# Delete old audio manually
find /opt/kovo/data/audio -mtime +7 -delete
# Delete pycache
find /opt/kovo/src -name __pycache__ -exec rm -rf {} + 2>/dev/null
```

Or send `/purge all` in Telegram.

---

## 23. Security

### Token Masking
`TokenMaskFilter` (in `src/gateway/config.py`) is a `logging.Filter` that replaces the live values of these env vars with `***REDACTED***` in every log record:
`TELEGRAM_BOT_TOKEN`, `GROQ_API_KEY`, `GITHUB_TOKEN`, `CLAUDE_CODE_OAUTH_TOKEN`, `TELEGRAM_API_HASH`.

Applied at startup in `main.py` to `logging.root.handlers` and all uvicorn logger handlers. No log line ever leaks a token, even in error backtraces.

### Startup Validation
`validate_env()` runs at the very beginning of the FastAPI lifespan, before any external connection is attempted. It checks:
- `TELEGRAM_BOT_TOKEN` and `OWNER_TELEGRAM_ID` — required; must not be empty or start with `your_`
- `CLAUDE_CODE_OAUTH_TOKEN` — recommended; warning logged if absent

On failure the full list of problems is printed with the fix command (`nano /opt/kovo/config/.env`) and the process exits with code 1.

`check_env_permissions()` emits a warning log (non-fatal) if `.env` is group- or world-readable.

### File Permissions
`bootstrap.sh` sets restrictive permissions after writing `.env.template`:

| File / Dir | Mode | Meaning |
|------------|------|---------|
| `config/.env.template` | `600` | owner read/write only |
| `config/.env` | `600` | owner read/write only |
| `config/google-credentials.json` | `600` | owner read/write only |
| `data/kovo.db` | `600` | owner read/write only |
| `.claude/settings.local.json` | `600` | owner read/write only |
| `config/` directory | `700` | owner access only |

Bootstrap verification checks confirm `.env.template` = 600 and `config/` = 700. If you copy `.env` after running bootstrap, it inherits the `600` set on the template; the bootstrap also `chmod 600`s `.env` directly if it already exists.

### Shell Safety Tiers
`src/tools/shell.py` classifies every command before execution:

| Tier | Classification | Examples | Behaviour |
|------|---------------|----------|-----------|
| Read-only | `safe` | `ls`, `df`, `docker ps` | Execute immediately |
| State-changing | `caution` | `systemctl stop`, `git push` | Execute, log warning |
| Destructive | `dangerous` | `rm -rf`, `mkfs`, `shutdown` | Blocked, returned as error |

Public lists `BLOCKED_COMMANDS` and `CONFIRM_COMMANDS` are importable for use by other modules. `is_blocked(cmd)` and `needs_confirmation(cmd)` expose simple predicate checks.

---

## 24. Security Audit

Kovo includes a built-in security audit skill that monitors your VM for unauthorized changes and potential security issues.

### What It Checks

**Network** — open ports, outbound connections, firewall status. Alerts on new unexpected listeners.

**Packages** — compares installed packages against a saved baseline. If a new package appears that Kovo didn't install, it flags it as unauthorized.

**Users & Access** — new user accounts, sudo grants, SSH configuration (root login, password auth), failed login attempts.

**File System** — new SUID/SGID binaries, world-writable files in sensitive directories, cron job changes, Kovo config file permissions.

**Processes** — unknown processes not in the baseline, high resource consumers, processes running as root.

**Malware** — ClamAV virus scan, rootkit detection (chkrootkit/rkhunter), suspicious files in /tmp and /dev/shm.

### How It Works

**First run** creates a baseline — a snapshot of your system's current state (ports, packages, users, SUID files, cron jobs). Everything is assumed authorized on first run.

**Every subsequent run** compares the current state against the baseline. Only changes are reported. After each audit, the baseline is updated.

**Reset the baseline** after intentional system changes: send `/audit reset` in Telegram.

### Schedule

Runs automatically every Sunday at 7:00 AM. Trigger anytime with `/audit`.

### Escalation

**Phone call** — suspicious activity (new user, new SUID binary, malware, unauthorized package, 20+ failed SSH logins) triggers an immediate Telegram voice call, then a detailed text message.

**Text warning** — less urgent issues (security updates available, world-writable files, config permissions too open).

**Clean report** — nothing changed; short summary confirming all is fine.

### Commands

| Command | Description |
|---------|-------------|
| `/audit` | Run a full security audit now |
| `/audit reset` | Reset baseline (use after intentional changes) |
| `/audit baseline` | Show current baseline summary |
| `/audit ports` | Quick port scan only |
| `/audit packages` | Quick package diff only |

### Security Tools (pre-installed by bootstrap)

Bootstrap installs ClamAV, chkrootkit, and rkhunter automatically. ClamAV virus definitions are updated during bootstrap and kept current by the `clamav-freshclam` service.

If virus definitions are outdated, update manually:
```bash
sudo systemctl stop clamav-freshclam
sudo freshclam
sudo systemctl start clamav-freshclam
```

---

## 25. Migration: KOVO → Kovo

If you have an existing `/opt/kovo` install, migrate with these steps:

```bash
# 1. Stop the service
sudo systemctl stop kovo

# 2. Rename the directory
sudo mv /opt/kovo /opt/kovo
sudo ln -s /opt/kovo /opt/kovo   # optional symlink for scripts in flight

# 3. Rename the service file
sudo mv /etc/systemd/system/kovo.service /etc/systemd/system/kovo.service
# Edit the service: update all /opt/kovo → /opt/kovo and Description
sudo sed -i 's|/opt/kovo|/opt/kovo|g; s|KOVO|Kovo|g' \
    /etc/systemd/system/kovo.service
sudo systemctl daemon-reload

# 4. Rename the database
mv /opt/kovo/data/kovo.db /opt/kovo/data/kovo.db

# 5. Update logrotate
sudo mv /etc/logrotate.d/kovo /etc/logrotate.d/kovo
sudo sed -i 's|/opt/kovo|/opt/kovo|g' /etc/logrotate.d/kovo

# 6. Update sudoers
sudo mv /etc/sudoers.d/kovo /etc/sudoers.d/kovo 2>/dev/null || true

# 7. Start the renamed service
sudo systemctl enable --now kovo
sudo systemctl status kovo
```

After migration, update your `.env` file: rename `OWNER_TELEGRAM_ID` → `OWNER_TELEGRAM_ID` and update `config.py` / `settings.yaml` to reference `OWNER_TELEGRAM_ID`.

---

## 22. Changelog

### v0.1 (2026-03-24)

- **Renamed KOVO → Kovo** — new name, new identity. `OWNER_TELEGRAM_ID` replaces `OWNER_TELEGRAM_ID` so every install is generic and friend-ready.
- **GitHub-based install** — bootstrap now clones source code from `github.com/Ava-AgentOne/kovo` instead of generating it with Claude Code. Every friend gets the identical codebase, dashboard, and logo. `bootstrap.sh` v4.0 with 16 steps including git clone, requirements.txt install, and dashboard build.
- **Kovo branding** — Kovo Blue (#378ADD), logo SVGs (square, circle), friendly blue alien mascot with antennae and rosy cheeks. IDENTITY.md template updated.
- **Migration** — existing `/opt/kovo` installs: rename directory, update service file, rename database. See migration script in `scripts/`.

### v1.5 (2026-03-24)

- **Smart context loading** — system prompt only includes context relevant to the current message. Always loads SOUL.md + USER.md + IDENTITY.md (~300 tokens); everything else (MEMORY.md, daily logs, skills, TOOLS.md, AGENTS.md, HEARTBEAT.md, DB schema, permissions, storage info) loaded on demand via pure-Python keyword matching. Fallback: ambiguous messages get MEMORY.md + TOOLS.md. Saves 60–90% of system prompt tokens on routine messages.
- **Auto-memory extraction** — once per day at 11 PM, Claude Sonnet scans the daily conversation log (capped at ~4000 tokens) and extracts preferences, decisions, facts, project details, and action items. Deduplication uses difflib ratio matching (no LLM call). Stores in categorized MEMORY.md and SQLite. Weekly memory budget check: archives MEMORY.md to `memory/archive/` when it exceeds 500 lines. Manual trigger: `/flush`.
- **SQLite structured storage** — persistent database at `data/kovo.db` (WAL mode) with four system tables: `memories`, `heartbeat_log`, `permission_log`, `conversation_stats`. Permission approve/deny events logged automatically. Heartbeat results logged automatically. Natural language queries via `/db query`. Agent can create custom `user_` tables on demand.
- **MEMORY.md categorized format** — bootstrap now creates MEMORY.md with sections: Preferences, Decisions, Facts, Projects, Action Items. Auto-extraction writes to the appropriate section.
- **Telegram UX** — persistent `ReplyKeyboardMarkup` (6 buttons: /status /health /memory /storage /skills /tools) attached to every agent reply. `InlineKeyboardMarkup` for permission requests, purge confirm, and sub-agent approval — buttons edit/disappear after tap. `▓░` Unicode progress bars for `/health` (RAM/CPU/Disk), `/storage`, `/status`. `src/telegram/formatting.py` with all format helpers.
- **Report builder skill** — built-in HTML report generator with 13 composable components, dark/light mode, animated charts, score rings, sparklines, and responsive layout. Ships with every fresh install.
- **New Telegram commands:** `/memory extracted`, `/memory search`, `/memory stats`, `/db`, `/db query`.
- **Security hardening** — `TokenMaskFilter` masks secrets from all log output; `validate_env()` fail-fast startup check; `check_env_permissions()` loose-perms warning; `bootstrap.sh` `chmod 600/700` on secrets and config dir; shell blocklist (`BLOCKED_COMMANDS`, `CONFIRM_COMMANDS`) with public `is_blocked()` / `needs_confirmation()` predicates.
- **Security audit skill** — built-in skill for deep VM security auditing. Baseline tracking with 6 audit categories (network, packages, users, files, processes, malware). Three-tier escalation: Telegram voice call for suspicious activity, text warning for minor issues, clean report when all OK. Weekly schedule (Sunday 7 AM). Bootstrap installs ClamAV, chkrootkit, rkhunter. Commands: `/audit`, `/audit reset`, `/audit baseline`, `/audit ports`, `/audit packages`.

### v1.4 (2026-03-23)

- **First-run onboarding** — guided Telegram interview for new installs. Asks for agent name, user profile, and personality style. Generates SOUL.md, USER.md, IDENTITY.md, MEMORY.md automatically. State persists across restarts. No manual file editing needed.
- **Permission system** — bootstrap v3.0 pre-creates 60+ entry allowlist so Claude Code never prompts during build. At runtime, blocked commands trigger a Telegram approval request; `/approve` updates `settings.local.json` and retries, `/deny` skips. `/permissions` command to view the full list.
- **Storage management** — three-tier garbage collection. Tier 1 (tmp, audio, screenshots) auto-purges on 6-hour heartbeat. Tier 2 (photos, documents, images) scanned weekly with user approval required. Low-disk alert at 15% free. `/storage` and `/purge` commands.
- **Housekeeping** — Ava → Kovo identity fix across all workspace files. Removed dead `ollama` parameter from ModelRouter. Systemd service hardened (`User=esam`, `TimeoutStopSec=30`, `RestartSec=5`). Log rotation via logrotate with `copytruncate`. `requirements.txt` rebuilt from actual imports. Removed stale `classifier_model` from settings.yaml.
- **Bootstrap v3.0** — complete rewrite. Creates permissions file, onboarding templates, all data directories, `.env.template`, logrotate config, backup and migrate scripts.
- **DOCS.md** — created (this file).

### v1.3 (2026-03-22)

- Single main agent (Kovo) — removed multi-agent routing
- Sub-agent on-demand creation with approval flow
- Telegram voice calls via tgcalls + Pyrogram userbot
- Google Workspace integration (Docs, Drive, Gmail, Calendar)
- GitHub integration via PyGithub
- Browser automation via Playwright
- Voice input (Whisper transcription) + voice output (TTS)
- Photo and document handling
- Dashboard (React frontend, WebSocket chat)
- Heartbeat scheduler (APScheduler, Ollama summaries)
- Skills system (SKILL.md format)
- Memory system (daily logs + long-term MEMORY.md)
