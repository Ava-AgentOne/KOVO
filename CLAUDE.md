# Kovo — Personal AI Agent System

> **Document version**: 1.5 (2026-03-24)

## Overview

Kovo is a self-hosted personal AI agent inspired by OpenClaw and GoBot. It runs on an Ubuntu 25.10 (Questing) VM (8GB RAM, 50GB disk) on an Unraid server. It uses the **Claude Code CLI as a subprocess** (`claude -p`) for complex tasks and **Ollama** (running on a NUC at `10.0.1.212:11434`) for cheap/simple tasks like heartbeats and quick answers.

The owner's name is Esam. He is based in Al Ain, UAE.

## System Requirements (already installed by bootstrap.sh)
- **OS**: Ubuntu 25.10 (Questing)
- **Python**: 3.13.x (system default — do NOT install 3.12)
- **Node.js**: 22+ (installed via NodeSource — includes npm, do NOT install Ubuntu's `npm` package separately as it conflicts)
- **PyTorch**: CPU-only (no GPU in VM — always use `--index-url https://download.pytorch.org/whl/cpu`)
- **Whisper**: Installed with `--no-deps` to avoid pulling GPU triton dependency
- **Claude Code**: Installed globally via npm, authenticated with Esam's Max subscription
- **Venv**: All Python packages in `/opt/kovo/venv` (never install system-wide)

**bootstrap.sh v4.0** additionally creates:
- `.claude/settings.local.json` — 61-entry permissions allowlist (prevents build-time prompts)
- `workspace/SOUL.md` with `## UNCONFIGURED` marker (triggers first-run onboarding)
- `data/{tmp,audio,photos,documents,images,screenshots,backups}/` — storage manager directories
- `workspace/{USER.md,IDENTITY.md}` as onboarding placeholders

## Architecture

```
Telegram Bot  ←→  Dashboard Chat (WebSocket)
      │                    │
      ▼                    ▼
Gateway (Python FastAPI)
      │
      ├── Kovo — Main Agent (the ONLY agent Esam talks to)
      │     ├── Smart context loading: always SOUL+USER+IDENTITY, rest on-demand
      │     ├── Access to ALL tools (shell, browser, google_api, ...)
      │     ├── Delegates to sub-agents when available
      │     └── Recommends new sub-agents on repeated patterns
      │
      ├── Sub-Agents (on-demand, created by Kovo with Esam's approval)
      │     └── workspace/agents/{name}/SOUL.md + tools.yaml + memory/
      │
      ├── Tool Registry (workspace/TOOLS.md)
      │     ├── shell, browser, google_api, telegram_call
      │     ├── tts, ollama, claude_cli, whisper
      │     └── Status: installed | not_installed | configured | not_configured
      │
      ├── Smart Model Router
      │     ├── Ollama (NUC)    → heartbeats, simple Q&A, classification
      │     ├── Claude Sonnet   → medium tasks (via claude -p --model sonnet)
      │     └── Claude Opus     → complex reasoning (via claude -p --model opus)
      │
      ├── Smart Context Loader
      │     └── Keyword-based prompt assembly — loads only what the message needs
      │
      ├── Memory System (Markdown + SQLite — OpenClaw compatible)
      │     ├── MEMORY.md (categorized: preferences, decisions, facts, projects, action items)
      │     ├── memory/YYYY-MM-DD.md (daily logs)
      │     ├── SQLite structured store (data/kovo.db)
      │     └── Auto-extractor (daily Claude Sonnet call at 23:00)
      ├── Skills System (SKILL.md format — OpenClaw compatible, procedures/knowledge)
      ├── Heartbeat System (cron-based, uses Ollama)
      └── Dashboard (React web UI on port 3000)
            ├── Overview — main agent + sub-agents status
            ├── Chat — full WebSocket chat with Kovo (backup to Telegram)
            ├── Tools — tool registry with install/config status
            ├── Agents — sub-agents with SOUL preview and tools
            ├── Memory, Skills, Heartbeat, Logs
            └── (no Costs page — Claude usage via Max subscription)
```

## Key Architecture Decisions

### Single Main Agent (Kovo)
- **One agent** handles everything. No more routing to specialists.
- Kovo uses **smart context loading** — always loads SOUL.md + USER.md + IDENTITY.md; loads MEMORY.md, daily log, matching skill, TOOLS.md, AGENTS.md, DB schema only when relevant keywords detected. Saves 60–90% of system prompt tokens on routine messages.
- Only the **best-matching skill** (highest trigger-hit count) is loaded per message, not all skills.
- All tools are available to Kovo.

### Smart Context Loading
- `build_system_prompt(user_message)` scans the message with pure Python keyword matching (no LLM call)
- **Always loads:** SOUL.md, USER.md, IDENTITY.md (~300 tokens)
- **On demand:** MEMORY.md, daily logs, best-matching skill, TOOLS.md, AGENTS.md, HEARTBEAT.md, DB schema, permissions info, storage info
- **Fallback:** if nothing matched (truly ambiguous message), loads MEMORY.md + TOOLS.md as safety net
- Keyword sets: `_MEMORY_KW`, `_LOG_KW`, `_TOOLS_KW`, `_AGENTS_KW`, `_HEARTBEAT_KW`, `_DB_KW`, `_PERMISSIONS_KW`, `_STORAGE_KW`
- Zero token cost for classification — pure Python string matching

### Tools vs Skills
- **Tools** = installed capabilities (shell, browser, google_api, etc.). Tracked in `workspace/TOOLS.md` with status. When a tool is missing, Kovo tells Esam what's needed.
- **Skills** = procedures and knowledge (SKILL.md format). Describe *how* to do things, not *what can be done*.

### Sub-Agents (On-Demand)
- Sub-agents are created only when Esam approves a recommendation.
- Each sub-agent lives in `workspace/agents/{name}/` with its own SOUL.md, tools.yaml, memory/.
- Kovo delegates to sub-agents when appropriate and summarises results.
- Kovo recommends a sub-agent after `_PATTERN_THRESHOLD` (5) repeated topic queries.
- Sub-agents are registered in `workspace/AGENTS.md`.

### Tool Registry
- YAML frontmatter in `workspace/TOOLS.md` tracks all tools.
- Status: `installed`, `not_installed`, `configured`, `not_configured`.
- `src/tools/registry.py` reads/writes this file.
- When Kovo needs an unavailable tool: "I need X to do this. Want me to install it?"

### Dashboard Chat
- WebSocket endpoint at `/api/ws/chat`.
- In-memory chat history (last 200 messages).
- Uses the same Kovo agent (user_id=0 for dashboard).
- Backup communication channel — identical experience to Telegram.

## Critical Design Decisions

### Package Management Rules
- **NEVER** run `pip install` system-wide. Ubuntu 25.10 blocks this (PEP 668). Always activate the venv first: `source /opt/kovo/venv/bin/activate`
- **NEVER** install PyTorch with GPU/CUDA. Always use: `pip install torch --index-url https://download.pytorch.org/whl/cpu`
- **NEVER** install `npm` as a separate package — Node.js 22 (nodesource) already includes it. Installing Ubuntu's npm package causes dependency conflicts.
- When installing new Python packages, always use the venv pip: `/opt/kovo/venv/bin/pip install <package>`
- When installing new Node packages globally: `npm install -g <package>`
- The agent CAN install system packages via `sudo apt install` — this is a key feature

### Claude Code Sandbox Permissions

Claude Code (`claude -p`) runs in a sandbox. Commands must be pre-approved in `.claude/settings.local.json`, or Claude will block them.

The file lives at `/opt/kovo/.claude/settings.local.json` and contains an `allow` list of `Bash(cmd *)` and `Edit(*)` patterns. Bootstrap v4.0 writes 61 pre-approved entries covering all common Unix commands, pip, playwright, redis-cli, and docker. New entries are added at runtime via the self-updating permission system (see below).

### Self-Updating Permissions

When the agent (via `claude -p`) encounters a command blocked by the sandbox:
1. `src/tools/claude_cli.py` detects the permission error in stderr
2. Extracts the base command and builds a pattern (e.g., `Bash(docker *)`)
3. Sends a Telegram message asking Esam to approve
4. On `/approve`: updates `.claude/settings.local.json`, retries the command
5. On `/deny`: skips and suggests an alternative

Handles nested permission errors — if the retry hits another block, it asks again.

Only the authorized Telegram user (OWNER_TELEGRAM_ID) can approve permissions.
Every grant is logged to daily memory.

**Commands:** `/permissions` (view list), `/approve`, `/deny`

### Claude Code Subprocess (NOT API)
Kovo uses Esam's Claude Max subscription through the official Claude Code CLI. This is the GoBot approach and stays within Anthropic's terms of service.

```python
import subprocess, json

def call_claude(prompt: str, session_id: str = None, model: str = None, system_prompt: str = None) -> dict:
    cmd = ["claude", "-p", prompt, "--output-format", "json"]
    if session_id:
        cmd.extend(["--resume", session_id])
    if model:
        cmd.extend(["--model", model])
    if system_prompt:
        cmd.extend(["--system-prompt", system_prompt])
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    return json.loads(result.stdout)
```

### Ollama for Cheap Tasks
Simple tasks go to Ollama on the NUC to save Claude usage:
- Heartbeat checks
- Message classification (is this simple or complex?)
- Quick factual answers
- Server health summaries
- Reminder scheduling

```python
import httpx

OLLAMA_URL = "http://10.0.1.212:11434"

async def call_ollama(prompt: str, model: str = "llama3.1:8b") -> str:
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{OLLAMA_URL}/api/generate", json={
            "model": model,
            "prompt": prompt,
            "stream": False
        }, timeout=120)
        return response.json()["response"]
```

### Smart Router Logic
The router classifies incoming messages and routes them:
1. First, Ollama classifies the message complexity (simple/medium/complex)
2. Simple → Ollama handles directly
3. Medium → Claude Sonnet via `claude -p`
4. Complex → Claude Opus via `claude -p`
5. Specialist tasks → routed to the appropriate sub-agent

## Workspace Structure

```
/opt/kovo/workspace/
├── SOUL.md              # Kovo's persona, values, boundaries
├── AGENTS.md            # Sub-agent registry (main agent + all sub-agents)
├── USER.md              # Esam's profile, preferences
├── IDENTITY.md          # Agent name, emoji, avatar
├── TOOLS.md             # Tool registry (YAML frontmatter + human notes)
├── HEARTBEAT.md         # Periodic task checklist
├── MEMORY.md            # Long-term curated memory
├── memory/
│   ├── YYYY-MM-DD.md    # Daily session logs
│   └── archive/         # Old logs (>30 days)
├── agents/              # Sub-agent definitions (created on demand)
│   └── {name}/
│       ├── SOUL.md      # Sub-agent persona
│       ├── tools.yaml   # Tool list + purpose
│       └── memory/      # Sub-agent's own memory
├── skills/
│   ├── server-health/
│   │   └── SKILL.md
│   ├── report-builder/          # built-in — ships with every install
│   │   ├── SKILL.md
│   │   └── templates/
│   │       └── report-template.html
│   ├── security-audit/          # built-in — ships with every install
│   │   └── SKILL.md
│   ├── google-workspace/
│   │   └── SKILL.md
│   ├── browser/
│   │   └── SKILL.md
│   ├── phone-call/
│   │   └── SKILL.md
│   └── ... (more skills)
├── checklists/
└── docs/
```

## Project Structure

```
/opt/kovo/
├── workspace/                  # Workspace (see above)
├── src/
│   ├── gateway/
│   │   ├── __init__.py
│   │   ├── main.py            # FastAPI app, startup, shutdown
│   │   ├── config.py          # Settings, env validation, token masking
│   │   └── routes.py          # Health check, webhook endpoints
│   ├── telegram/
│   │   ├── __init__.py
│   │   ├── bot.py             # python-telegram-bot handler
│   │   ├── commands.py        # /status, /tools, /agents, /call, etc.
│   │   ├── formatting.py      # MAIN_KEYBOARD, BUTTON_TO_COMMAND, progress_bar(), format_* functions
│   │   └── middleware.py      # Auth, rate limiting, logging
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── kovo.py        # Kovo — the ONE main agent
│   │   └── sub_agent.py       # SubAgentRunner — loads/runs sub-agents
│   ├── onboarding/
│   │   ├── __init__.py
│   │   ├── flow.py            # OnboardingFlow state machine (welcome→generate)
│   │   └── generator.py       # Writes SOUL.md, USER.md, IDENTITY.md, MEMORY.md
│   ├── router/
│   │   ├── __init__.py
│   │   ├── classifier.py      # Ollama-based message complexity classifier
│   │   └── model_router.py    # Routes to Sonnet / Opus based on message complexity
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── manager.py          # Read/write workspace MD files + identity()
│   │   ├── daily_log.py        # Daily memory/YYYY-MM-DD.md management
│   │   ├── search.py           # Simple keyword + semantic search
│   │   ├── auto_extract.py     # Daily Claude Sonnet extraction + dedup + budget
│   │   └── structured_store.py # SQLite WAL (memories, heartbeat_log, permission_log, conversation_stats, security_audit_log)
│   ├── skills/
│   │   ├── __init__.py
│   │   ├── loader.py          # Load SKILL.md files from workspace
│   │   ├── registry.py        # Skill registry, lookup, matching
│   │   └── creator.py         # Agent can create new skills
│   ├── heartbeat/
│   │   ├── __init__.py
│   │   ├── scheduler.py       # APScheduler cron-based heartbeat
│   │   ├── checks.py          # System health check functions
│   │   └── reporter.py        # Send reports via Telegram
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── registry.py        # ToolRegistry — reads workspace/TOOLS.md
│   │   ├── claude_cli.py      # Claude Code subprocess wrapper + permission detection
│   │   ├── ollama.py          # Ollama API client
│   │   ├── google_api.py      # Google Workspace API (OAuth2)
│   │   ├── telegram_call.py   # Telegram voice call (tgcalls + userbot)
│   │   ├── tts.py             # Text-to-speech (piper/edge-tts/ElevenLabs)
│   │   ├── browser.py         # Playwright browser automation
│   │   ├── storage.py         # StorageManager — GC, disk monitoring, purge
│   │   ├── shell.py           # Safe shell command execution
│   │   └── security_audit.py  # SecurityAuditor — baseline, compare, escalate
│   └── dashboard/
│       ├── __init__.py
│       ├── api.py             # REST API + WebSocket /api/ws/chat
│       └── frontend/          # React dashboard
│           └── src/pages/
│               ├── Overview.jsx   # Main agent + sub-agents + activity
│               ├── Chat.jsx       # WebSocket chat with Kovo
│               ├── Tools.jsx      # Tool registry with status
│               ├── Agents.jsx     # Sub-agents with SOUL/tools
│               ├── Memory.jsx     # Browse/edit workspace files
│               ├── Skills.jsx     # Skill registry
│               ├── Heartbeat.jsx  # Schedule + history
│               └── Logs.jsx       # Real-time log viewer
├── config/
│   ├── settings.yaml          # Main config file
│   ├── .env                   # Secrets (tokens, API keys)
│   └── .env.template          # Template for new installs
├── data/                      # All runtime data (managed by StorageManager)
│   ├── kovo.db            # SQLite structured store (WAL mode)
│   ├── tmp/                   # Temp processing files (auto-purge: 1 day)
│   ├── audio/                 # Voice messages, TTS output (auto-purge: 7 days)
│   ├── photos/                # Images from Telegram (review: 30 days)
│   ├── documents/             # PDFs, DOCX from Telegram (review: 30 days)
│   ├── images/                # Generated/screenshot images (review: 30 days)
│   ├── screenshots/           # Browser automation (auto-purge: 7 days)
│   └── backups/               # workspace/ backups from backup.sh (keep: 30 days)
├── scripts/
│   ├── migrate_openclaw.sh    # Copy + patch OpenClaw workspace
│   └── backup.sh              # Backup workspace to Unraid share
├── .claude/
│   └── settings.local.json    # Claude Code sandbox permissions (61 entries)
├── tests/
├── requirements.txt
├── package.json               # For dashboard frontend
├── systemd/
│   └── kovo.service       # Systemd service file
├── bootstrap.sh               # VM installer (v4.0)
├── CLAUDE.md                  # This file
└── README.md
```

## Component Details

### 1. Gateway (src/gateway/)

FastAPI application that ties everything together.

- Runs on port 8080
- Receives Telegram webhook updates
- Manages agent lifecycle
- Serves dashboard API on /api/*
- Health check at /health

### 2. Telegram Bot (src/telegram/)

Uses `python-telegram-bot` library.

Features:
- Receive text, voice, photo, document messages
- Voice messages → transcribe with Whisper
- Commands: `/status`, `/tools`, `/agents`, `/health`, `/skills`, `/memory`, `/call`, `/storage`, `/purge`, `/permissions`, `/approve`, `/deny`
- Markdown formatting for responses
- Only responds to Esam (allowlist by Telegram user ID)

Key commands:
- `/tools` — show tool registry with install/config status
- `/agents` — list sub-agents
- `/status` — system status (tools ready, sub-agents, skills)
- `/clear` — clear Kovo's session history
- `/memory` — today's log; `/memory extracted` — last SQLite memories; `/memory search <q>` — search; `/memory stats`
- `/flush` — extract + deduplicate today's learnings into MEMORY.md + SQLite (uses Claude Sonnet)
- `/db` — show SQLite schema; `/db query <question>` — natural language SELECT query
- `/storage` — disk usage report with per-directory breakdown
- `/purge <all|photos|documents|images>` — clean old files (with confirmation step)
- `/permissions` — view Claude Code sandbox allowlist
- `/approve` / `/deny` — grant or reject a runtime permission request (logged to SQLite)
- `/audit` — run full security audit
- `/audit reset` — reset security baseline (use after intentional changes)
- `/audit baseline` — show current baseline summary
- `/audit ports` — quick port scan
- `/audit packages` — quick package diff

### 3. Agent System (src/agents/)

#### KovoAgent (`kovo.py`)
The one and only agent. Key properties:
- `build_system_prompt(user_message)` — smart context loading: always SOUL+USER+IDENTITY; MEMORY.md, daily log, best-matching skill, TOOLS, AGENTS, DB schema loaded only on keyword match
- `_needs_memory/daily_logs/tools/agents/db_schema()` — pure-Python keyword classifiers (zero cost)
- `_find_matching_skill(message)` — calls `registry.match_best()`, returns single highest-scoring skill
- `handle(message, user_id)` — processes a message, routes to sub-agent if applicable
- `_track_topics()` — counts topic occurrences per user
- `_maybe_recommend_sub_agent()` — fires after 5 occurrences of a topic
- `make_call()` — TTS voice call (wired up by gateway)
- `clear_session(user_id)` — reset Claude session

#### SubAgentRunner (`sub_agent.py`)
Loads and runs on-demand sub-agents:
- `load()` — scans `workspace/agents/` for sub-agent definitions
- `create(name, soul, tools, purpose)` — creates sub-agent on disk + registers in AGENTS.md
- `maybe_delegate(message, ...)` — asks Ollama if a sub-agent should handle the message
- `_run_sub_agent()` — runs sub-agent via claude_cli with its own SOUL.md as system prompt

### 3b. First-Run Onboarding (src/onboarding/)

When Kovo is installed fresh, the first Telegram message triggers a guided onboarding conversation instead of normal operation.

**Trigger:** `workspace/SOUL.md` contains the marker `## UNCONFIGURED` (set by bootstrap).

**Flow:**
1. **Welcome** — Agent greets user, asks them to pick a name for the agent
2. **User Profile** — Agent interviews: name, city, languages, occupation, email
3. **Personality** — User picks a style: Professional, Friendly, Sarcastic, Minimal, or Custom. Plus emoji preference and proactivity.
4. **Confirm** — Agent shows summary, user approves or requests changes
5. **Generate** — Agent writes SOUL.md, USER.md, IDENTITY.md, MEMORY.md from the answers

State is tracked in `workspace/.onboarding_state.json` — survives restarts.

After generation, `## UNCONFIGURED` is gone and the agent transitions to normal operation — no restart needed.

**Sub-agent onboarding** uses a lighter 3-question flow (name, personality, special instructions) triggered from `src/onboarding/flow.py` via `start_subagent_onboarding()`.

**Code:** `src/onboarding/flow.py`, `src/onboarding/generator.py`

### 4. Smart Router (src/router/)

```python
class ModelRouter:
    async def route(self, message: str, complexity: str) -> str:
        if complexity == "simple":
            return await self.ollama.generate(message)
        elif complexity == "medium":
            return self.claude_cli.call(message, model="sonnet")
        else:  # complex
            return self.claude_cli.call(message, model="opus")
```

### 5. Memory System (src/memory/)

Reads and writes OpenClaw-compatible Markdown files, plus a SQLite structured store.

**Smart context loading** (replaces always-load-everything):
- Always: SOUL.md, USER.md, IDENTITY.md (~300 tokens)
- On-demand: MEMORY.md (remembering keywords), daily log (today/earlier keywords), best-matching skill, TOOLS.md, AGENTS.md, DB schema

**Auto-memory extraction** (`auto_extract.py`):
- Runs daily at 23:00 (triggered by heartbeat scheduler)
- One Claude Sonnet call per day; input capped at 3200 chars (~4000 tokens)
- Extracts 3–8 bullet points in `[category] content` format
- Deduplication: SQL LIKE coarse filter + `difflib.SequenceMatcher` ratio > 0.8 (no LLM call)
- Stores to both `workspace/MEMORY.md` and SQLite `memories` table
- Budget: archives MEMORY.md to `workspace/memory/archive/memories_archived.md` when >500 lines
- Manual trigger: `/flush` command

**Structured store** (`structured_store.py`):
- SQLite at `data/kovo.db`, WAL mode, `row_factory = sqlite3.Row`
- 5 system tables: `memories`, `heartbeat_log`, `permission_log`, `conversation_stats`, `security_audit_log`
- `natural_query(question)` → Claude haiku translates to SELECT SQL, executes, returns formatted text
- `create_custom_table(name, cols)` → creates `user_`-prefixed tables on demand
- Permission audit: approve/deny events logged automatically via `claude_cli.py`
- Heartbeat logging: full reports and alerts logged to `heartbeat_log`

Daily log format:
```markdown
# 2026-03-21

## Session 14:30
- Esam asked about server health
- Reported disk usage at 78% on cache drive
- Recommended clearing Docker image cache

## Session 16:45
- Created Google Doc for project proposal
- Sent draft link via Telegram
```

End-of-day: auto-extractor (23:00) pulls learnings to MEMORY.md + SQLite

### 6. Skills System (src/skills/)

Skills are directories containing a SKILL.md file with:
```markdown
---
name: server-health
description: Monitor and report on Linux server and Unraid health
tools: [shell, ssh]
trigger: server, health, disk, cpu, ram, docker, unraid, array
---

# Server Health Skill

## Capabilities
- Check disk usage, CPU, RAM, network
- Monitor Docker container status
- Check Unraid array health
- Report SMART status of drives
- Alert on high usage thresholds

## Procedures
### Health Check
1. Run `df -h` for disk usage
2. Run `free -m` for memory
3. Run `docker ps` for container status
4. Check /proc/loadavg for CPU load
5. Summarize findings and alert if any threshold exceeded
```

The agent can create new skills dynamically when it discovers a new capability it needs.

One skill ships with every fresh install: **report-builder** — generates polished, self-contained HTML reports (system health, morning briefings, weekly digests, incident reports, analytics). Triggers on any "report", "dashboard", or "generate report" request. Output goes to `/opt/kovo/data/documents/`.

Second built-in skill: **security-audit** — comprehensive VM security scan (network, packages, users, files, processes, malware). Maintains a baseline at `data/security_baseline.json` — first run creates it, subsequent runs compare and report only changes. Triggers on "security", "audit", "scan", "vulnerability". Escalates to Telegram voice call on suspicious activity (new users, new SUID binaries, malware, unauthorized packages). Weekly schedule: Sunday 7:00 AM. Manual trigger: `/audit`. Implementation: `src/tools/security_audit.py`.

### 7. Heartbeat System (src/heartbeat/)

Uses APScheduler with cron triggers.

Default schedule (configurable in HEARTBEAT.md):

| Schedule | Job | Description |
|----------|-----|-------------|
| Every 30 min | **Quick check** | CPU, RAM, disk via Ollama |
| Every 6 hours | **Full report** | Health summary via Claude |
| Every 6 hours | **Auto-purge** | Storage Tier 1 cleanup + disk alert if free < 15% |
| Every morning 8 AM | **Briefing** | Daily summary, yesterday's activity |
| Daily 3 AM | **Log archive** | Archive daily logs older than 30 days |
| Daily 9 AM | **SIM reminder** | Alert if prepaid SIM approaching 90-day expiry |
| Daily 11 PM | **Auto-extract** | Extract learnings → MEMORY.md + SQLite (Claude Sonnet, deduped) |
| Sunday 3 AM | **Storage review** | Scan Tier 2 files, notify if old files found |
| Sunday 3:30 AM | **Memory budget** | Archive MEMORY.md if >500 lines |
| Sunday 7 AM | **Security audit** | Full VM security scan, baseline comparison, call on suspicious activity |
| Every 80 days | **SIM top-up** | Remind Esam to top up prepaid SIM |

Heartbeat flow:
1. Cron fires → read HEARTBEAT.md checklist
2. Ollama evaluates: does anything need attention?
3. If yes → escalate to Claude for detailed analysis
4. Send findings to Esam via Telegram
5. Log to memory/YYYY-MM-DD.md

### 7b. Storage Management (src/tools/storage.py)

Three-tier garbage collection system. Runs automatically via heartbeat scheduler.

**Tier 1 — Auto-purge (no approval needed):**
| Directory | Retention |
|-----------|-----------|
| `data/tmp/` | 1 day |
| `data/audio/` | 7 days |
| `data/screenshots/` | 7 days |
| `__pycache__/` in src/ | Immediate |

**Tier 2 — Ask before purge:**
| Directory | Retention |
|-----------|-----------|
| `data/photos/` | 30 days, then ask |
| `data/documents/` | 30 days, then ask |
| `data/images/` | 30 days, then ask |

**Tier 3 — Never auto-delete:**
- `workspace/memory/` — archived after 30 days
- `workspace/MEMORY.md` — permanent
- `data/backups/` — keep 30 days

**Schedule:**
- Every 6 hours: auto-purge + disk check (alert if free < 15%)
- Weekly Sunday 3 AM: scan Tier 2, notify user if old files found

**Commands:** `/storage` (disk report), `/purge all|photos|documents|images`

**Data directories** (created by bootstrap, expected by all tools):
`data/tmp/`, `data/audio/`, `data/photos/`, `data/documents/`, `data/images/`, `data/screenshots/`, `data/backups/`

### 8. Telegram Voice Calls (src/tools/telegram_call.py)

Uses tgcalls + Pyrogram userbot for real Telegram calls to Esam. Falls back to voice messages if the call isn't answered.

**Architecture:**
- A **Telegram userbot** (separate account from the bot) using Pyrogram + tgcalls
- The userbot can initiate real Telegram voice calls to Esam
- TTS engine generates audio (edge-tts for free, or ElevenLabs for natural voice)
- Audio is converted to RAW format (s16le, 48kHz, stereo) for tgcalls
- If call not answered within 30 seconds → fallback to voice message via the bot

**Requirements:**
- A second Telegram account (eSIM or spare number)
- Telegram API credentials from https://my.telegram.org (api_id + api_hash)
- Pyrogram (MTProto client)
- tgcalls or py-tgcalls (C++ WebRTC binding)
- edge-tts or piper (free TTS) or ElevenLabs API (premium TTS)
- ffmpeg (audio conversion)

**Use cases:**
- Urgent server alerts (disk full, container down, array degraded)
- Agent needs approval for a risky action
- Esam sends `/call` command in Telegram
- Scheduled wake-up/reminder calls
- Any notification marked as "urgent" by the agent

```python
from pyrogram import Client as PyroClient
from pytgcalls import PyTgCalls
import edge_tts
import subprocess
import asyncio

# Userbot for making calls (separate Telegram account)
userbot = PyroClient(
    "kovo_caller",
    api_id=API_ID,
    api_hash=API_HASH,
    # Session string or phone number auth
)

async def generate_tts_audio(text: str, output_path: str, voice: str = "en-US-GuyNeural"):
    """Generate TTS audio using edge-tts (free, Microsoft voices)"""
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)
    # Convert to RAW for tgcalls
    raw_path = output_path.replace(".mp3", ".raw")
    subprocess.run([
        "ffmpeg", "-y", "-i", output_path,
        "-f", "s16le", "-ac", "2", "-ar", "48000",
        "-acodec", "pcm_s16le", raw_path
    ], capture_output=True)
    return raw_path

async def call_esam(message: str, urgent: bool = False):
    """
    Primary: Initiate real Telegram call and play TTS audio
    Fallback: Send voice message via bot if call not answered
    """
    # Step 1: Generate TTS audio
    audio_path = await generate_tts_audio(message, "/tmp/kovo_call.mp3")
    
    # Step 2: Try real Telegram call via userbot + tgcalls
    try:
        # Initiate call, play audio, hang up
        # (tgcalls handles the WebRTC call setup)
        call_success = await initiate_telegram_call(OWNER_USER_ID, audio_path)
        if call_success:
            return {"method": "call", "status": "delivered"}
    except Exception as e:
        log.warning(f"Telegram call failed: {e}")
    
    # Step 3: Fallback — send voice message via bot
    await bot.send_voice(
        chat_id=OWNER_TELEGRAM_ID,
        voice=open(audio_path.replace(".raw", ".mp3"), "rb"),
        caption=f"{'🚨 URGENT: ' if urgent else ''}{message[:200]}"
    )
    return {"method": "voice_message", "status": "delivered"}
```

### 8b. TTS Engine (src/tools/tts.py)

Pluggable TTS with multiple backends:
- **edge-tts** (default, free) — Microsoft Azure voices, good quality, many languages including Arabic
- **piper** (local, free) — runs entirely on the VM, no internet needed
- **ElevenLabs** (premium, optional) — most natural sounding, costs ~$5/month

```python
class TTSEngine:
    async def speak(self, text: str, output_path: str) -> str:
        """Generate speech audio file. Returns path to audio file."""
        if self.backend == "edge-tts":
            return await self._edge_tts(text, output_path)
        elif self.backend == "piper":
            return await self._piper(text, output_path)
        elif self.backend == "elevenlabs":
            return await self._elevenlabs(text, output_path)
```

The agent can also receive voice messages from Esam → transcribe with Whisper → process as text.

### 8c. Caller Session Health Monitor

The Telegram userbot session (used for voice calls) can expire if Telegram invalidates it. Kovo must monitor this proactively and alert Esam BEFORE it breaks.

**Monitoring logic (runs every 6 hours as part of heartbeat):**
```python
async def check_caller_session_health():
    """
    Verify the Telegram userbot session is still alive.
    Alert Esam via bot if it's dying.
    """
    try:
        # Try a simple API call with the userbot
        me = await userbot.get_me()
        # Session is alive — log it
        log.info(f"Caller session healthy: {me.phone_number}")
        return True
    except (AuthKeyUnregistered, SessionRevoked, UserDeactivated) as e:
        # Session is dead — URGENT alert via bot
        await bot.send_message(
            chat_id=OWNER_TELEGRAM_ID,
            text=(
                "🚨 URGENT: Kovo caller session has expired!\n\n"
                "Voice calls will NOT work until you re-authenticate.\n\n"
                "To fix: Pop your prepaid SIM into a phone, then run:\n"
                "`/reauth_caller` in this chat\n\n"
                "Or SSH into the VM and run:\n"
                "`cd /opt/kovo && python -m src.tools.telegram_call --reauth`"
            ),
            parse_mode="Markdown"
        )
        return False
    except Exception as e:
        # Network error or temporary issue — warn but don't panic
        log.warning(f"Caller session check failed: {e}")
        return None
```

**Re-authentication command:** When Esam sends `/reauth_caller` in Telegram, Kovo triggers the Pyrogram re-auth flow (sends OTP to the prepaid SIM number, Esam enters the code via Telegram).

**Prepaid SIM reminder:** Kovo tracks when the last top-up reminder was sent. Every 80 days it sends: "Reminder: top up your prepaid SIM (xxx-xxxx) to keep the caller account alive. UAE prepaid SIMs expire after 90 days without top-up."

### 9. Dashboard (src/dashboard/)

React web UI served on port 3000.

Pages:
- **Overview**: Main agent + sub-agents panel, status cards, today's activity
- **Chat**: Full WebSocket chat with Kovo — backup communication channel. Markdown rendering, conversation history, identical to Telegram experience.
- **Tools**: Tool registry (from workspace/TOOLS.md) with install/config status. "Mark as installed" button for manually installed tools.
- **Agents**: Sub-agents with SOUL preview and tools. "New Sub-Agent" form.
- **Memory**: Browse/edit workspace files (SOUL.md, MEMORY.md, daily logs)
- **Skills**: Skill registry, create/edit skills
- **Heartbeat**: Check history, next scheduled runs
- **Logs**: Real-time log viewer

WebSocket endpoint: `ws://{host}/api/ws/chat`
Chat history stored in-memory (last 200 messages). Dashboard user_id = 0.

Tech: React + Tailwind CSS + Vite. API served by FastAPI.

### 10. Google Workspace (src/tools/google_api.py)

OAuth2 service account for:
- **Google Docs**: Create, read, edit documents
- **Google Drive**: Upload, download, search files
- **Gmail**: Send emails, read inbox, search
- **Google Calendar**: Read events, create events (future)

Credentials stored in config/.env. OAuth token refresh handled automatically.

### 11. Shell & Server Access (src/tools/shell.py)

The agent has controlled shell access on the VM. Commands are classified in three tiers:

| Tier | Classification | Behaviour |
|------|---------------|-----------|
| Read-only / harmless | `safe` | Execute immediately |
| State-changing but reversible | `caution` | Execute with prominent warning log |
| Destructive / irreversible | `dangerous` | Blocked — returned as error |

Public API for callers:
- `BLOCKED_COMMANDS` — list of always-blocked command fragments
- `CONFIRM_COMMANDS` — list of commands classified as `caution`
- `is_blocked(cmd)` — True if cmd matches any BLOCKED_COMMANDS entry
- `needs_confirmation(cmd)` — True if cmd matches any CONFIRM_COMMANDS entry
- `classify(cmd)` → `"safe"` / `"caution"` / `"dangerous"`
- `run(cmd, allow_caution=True)` — executes unless dangerous; caution is logged

Other rules:
- The agent CAN install packages (`sudo apt install`, `pip install`) — this is a key feature
- The agent CAN create and manage systemd services
- The agent CAN modify its own configuration

### 14. Security (src/gateway/config.py · main.py · bootstrap.sh)

Invisible hardening — no UX changes, no new commands.

#### Token Masking
`TokenMaskFilter(logging.Filter)` in `config.py` replaces the values of
`TELEGRAM_BOT_TOKEN`, `GROQ_API_KEY`, `GITHUB_TOKEN`, `CLAUDE_CODE_OAUTH_TOKEN`,
`TELEGRAM_API_HASH` with `***REDACTED***` in every log record.
Applied in `main.py` to `logging.root.handlers` + all uvicorn logger handlers
immediately after `basicConfig`.

#### Startup Env Validation
`validate_env()` in `config.py` runs before `_build_deps()` in the lifespan.
- Checks `TELEGRAM_BOT_TOKEN` and `OWNER_TELEGRAM_ID` are set and not `your_*` placeholders
- Warns (non-fatal) if `CLAUDE_CODE_OAUTH_TOKEN` is missing
- On failure: logs full problem list with fix command and calls `sys.exit(1)`

`check_env_permissions()` warns (non-fatal) if `.env` is group- or world-readable.

#### File Permissions
`bootstrap.sh` sets after writing `.env.template`:
- `chmod 600` — `.env.template`, `.env`, `google-credentials.json`, `kovo.db`, `settings.local.json`
- `chmod 700` — `config/` directory

Verification checks confirm `.env.template` = 600 and `config/` = 700.

### 13. Telegram UX (src/telegram/)

Provides a polished, button-driven Telegram interface optimised for mobile (30-35 chars/line).

#### Persistent Reply Keyboard
`MAIN_KEYBOARD` (`ReplyKeyboardMarkup`, `resize_keyboard=True`, `is_persistent=True`) — attached to every outgoing agent reply. Buttons use emoji labels without `/` for a cleaner look:
```
┌────────────────┬────────────────┐
│  📡 Status     │  🖥 Health     │
├────────────────┼────────────────┤
│  🧠 Memory     │  💾 Storage    │
├────────────────┼────────────────┤
│  📚 Skills     │  🔧 Tools      │
└────────────────┴────────────────┘
```
A `MessageHandler` in `bot.py` intercepts button text and routes to the command handler via `_BUTTON_HANDLERS`. `BUTTON_TO_COMMAND` dict in `formatting.py` maps text → `/command` string.

#### Inline Keyboards
`InlineKeyboardMarkup` replaces text-based confirmations. Tapping a button calls `button_callback()` which edits the original message (buttons removed after tap):

| Scenario | Buttons | Callback data |
|---|---|---|
| Permission request | ✅ Approve / ❌ Deny | `perm_approve` / `perm_deny` |
| Purge confirmation | 🗑 Yes, delete / Cancel | `purge_confirm` / `purge_cancel` |
| Sub-agent approval | 👍 Create it / Not now | `agent_approve` / `agent_deny` |

#### Formatted Command Responses
All responses use `▓░` Unicode progress bars (10 chars default) wrapped in backtick code blocks for monospace alignment. Thresholds:
- CPU: > 80% ⚠️, > 95% 🚨
- RAM: > 80% ⚠️
- Disk: > 85% ⚠️, > 95% 🚨

`format_health()` calls `psutil.cpu_percent(interval=0.5)` — run in executor.

#### Key Files
- `src/telegram/formatting.py` — `MAIN_KEYBOARD`, `BUTTON_TO_COMMAND`, inline factories, `progress_bar()`, all `format_*` functions
- `src/telegram/bot.py` — `_BUTTON_HANDLERS`, `_handle_keyboard_button`, attaches keyboard/buttons to all outgoing messages
- `src/telegram/commands.py` — `button_callback()` for all inline actions; all command handlers use `format_*` functions

### 12. Browser Automation (src/tools/browser.py)

Playwright for headless browser automation:
- Web scraping and research
- Form filling
- Screenshot capture
- Web testing

## Configuration

### settings.yaml
```yaml
kovo:
  workspace: /opt/kovo/workspace
  data_dir: /opt/kovo/data

telegram:
  token: ${TELEGRAM_BOT_TOKEN}
  allowed_users:
    - ${OWNER_TELEGRAM_ID}

ollama:
  url: http://10.0.1.212:11434
  default_model: llama3.1:8b
  # NOTE: no classifier_model — Ollama is used only for heartbeats, not message routing

claude:
  # Uses claude CLI subprocess — no API key needed
  default_model: sonnet
  memory_flush_model: sonnet
  timeout: 300

google:
  credentials_file: /opt/kovo/config/google-credentials.json
  scopes:
    - https://www.googleapis.com/auth/drive
    - https://www.googleapis.com/auth/documents
    - https://www.googleapis.com/auth/gmail.modify
    - https://www.googleapis.com/auth/calendar
    - https://www.googleapis.com/auth/spreadsheets

telegram_call:
  # Userbot for making real Telegram voice calls
  api_id: ${TELEGRAM_API_ID}
  api_hash: ${TELEGRAM_API_HASH}
  session_name: kovo_caller
  owner_user_id: ${OWNER_TELEGRAM_ID}
  call_timeout: 30  # seconds before fallback to voice message
  tts:
    backend: edge-tts  # edge-tts (free), piper (local), elevenlabs (premium)
    voice: en-US-AvaMultilingualNeural

heartbeat:
  quick_interval: 30   # minutes
  full_interval: 6     # hours
  morning_time: "08:00"
  use_ollama: true

transcription:
  groq_api_key: ${GROQ_API_KEY}
  whisper_model: base   # fallback local model: tiny, base, small, medium

dashboard:
  port: 3000  # Vite dev server only — production dashboard served by gateway at port 8080
  host: 0.0.0.0

gateway:
  port: 8080
  host: 0.0.0.0

memory:
  auto_extract:
    enabled: true
    schedule: "23:00"        # daily (Asia/Dubai)
    input_cap_chars: 3200    # ~4000 tokens of log context
    dedup_threshold: 0.8     # difflib ratio for duplicate detection
  structured_store:
    db_path: /opt/kovo/data/kovo.db
    memory_budget_lines: 500 # archive MEMORY.md when it exceeds this
    consolidation_schedule: "sun 03:30"
```

## Build Instructions

### Phase 1: Core Gateway + Telegram + Router
Build the foundation first. Get a working Telegram bot that can:
1. Receive messages from Esam
2. Classify complexity with Ollama
3. Route simple messages to Ollama
4. Route complex messages to Claude via `claude -p`
5. Send responses back via Telegram
6. Load workspace files (SOUL.md, USER.md) into prompts

### Phase 2: Memory System
Add persistent memory:
1. Read/write daily logs (memory/YYYY-MM-DD.md)
2. Load MEMORY.md at session start
3. End-of-session memory flush
4. Simple keyword search across memory files

### Phase 3: Multi-Agent System
Add specialist agents:
1. BaseAgent class with memory + tool access
2. ManagerAgent for routing
3. ServerHealthAgent with shell access
4. GeneralAgent for conversation

### Phase 4: Server Health + Heartbeat
1. System health check functions
2. APScheduler cron-based heartbeat
3. Telegram notifications for alerts
4. Heartbeat uses Ollama (free)

### Phase 5: Skills System
1. SKILL.md loader and registry
2. Skill matching for incoming messages
3. Skill creator (agent can write new skills)

### Phase 6: Google Workspace
1. OAuth2 setup and token management
2. Google Docs, Drive, Gmail tools
3. GoogleAgent with appropriate permissions

### Phase 7: Telegram Voice Calls
1. Set up Pyrogram userbot (second Telegram account)
2. Install tgcalls/py-tgcalls for WebRTC calling
3. TTS engine (edge-tts default, ElevenLabs optional)
4. Call → voice message fallback logic
5. Urgent alert escalation via call

### Phase 8: Browser Automation
1. Playwright setup
2. BrowserAgent with web interaction tools

### Phase 9: Dashboard
1. FastAPI dashboard API endpoints
2. React frontend with workspace file management
3. Agent status and cost tracking

### Phase 10: Architecture Consolidation ✅
Refactored from multi-agent routing to single Kovo agent. Removed Ollama from message routing path (heartbeats only). Removed dead `ollama` parameter from ModelRouter. Cleaned up stale "Ava" references.

### Phase 11: First-Run Onboarding ✅
Guided Telegram interview for new installs. Configures agent name, user profile, and personality. State persists across restarts via `.onboarding_state.json`. Generates SOUL.md, USER.md, IDENTITY.md, MEMORY.md from collected answers. Sub-agent onboarding uses a lighter 3-question flow.

### Phase 12: Permission System ✅
Comprehensive build-time allowlist (61 entries in `.claude/settings.local.json`) + runtime self-updating via Telegram approval. Blocked commands propagate through the call stack to the bot layer, which sends a formatted request and retries on approval.

### Phase 13: Storage Management ✅
Three-tier garbage collection (`src/tools/storage.py`). Tier 1 auto-purges on 6-hour heartbeat. Tier 2 scans weekly and asks Esam before deleting. Low-disk alerts at 15% free. `/storage` and `/purge` Telegram commands.

### Phase 14: Smart Context Loading ✅
Rewrote `build_system_prompt(user_message)` with pure-Python keyword classifiers. Always loads SOUL+USER+IDENTITY; loads MEMORY.md, daily log, best-matching skill, TOOLS, AGENTS, DB schema only on keyword match. Saves 60–90% system prompt tokens on routine messages.

### Phase 15: Auto-Memory + Structured Storage ✅
`src/memory/auto_extract.py` — daily Claude Sonnet extraction at 23:00, dedup via difflib (no LLM), stores to MEMORY.md + SQLite. `src/memory/structured_store.py` — SQLite WAL, 5 system tables, natural language SELECT queries via Claude haiku, custom `user_` tables on demand. Permission audit trail logged automatically. `/flush`, `/memory extracted|search|stats`, `/db`, `/db query` Telegram commands.

### Phase 16: Telegram UX ✅
`src/telegram/formatting.py` — persistent `ReplyKeyboardMarkup` (6 buttons, 2 columns) attached to every agent reply; `InlineKeyboardMarkup` for permission requests, purge confirm, and sub-agent approval (buttons edit/disappear after tap); `▓░` Unicode progress bars for `/health`, `/storage`, `/status`; emoji-first formatting for all command responses. `button_callback()` in commands.py handles all inline actions.

### Phase 17: Security Hardening ✅
`TokenMaskFilter` applied to all log handlers masks secrets from logs. `validate_env()` + `check_env_permissions()` provide fail-fast startup validation. `bootstrap.sh` sets `chmod 600/700` on secrets and config dir. `shell.py` gains public `BLOCKED_COMMANDS`, `CONFIRM_COMMANDS`, `is_blocked()`, `needs_confirmation()` with `classify()` updated to use them.

### Phase 18: Security Audit Skill ✅
`workspace/skills/security-audit/SKILL.md` — built-in skill for deep VM security auditing. `src/tools/security_audit.py` — SecurityAuditor class with baseline tracking (`data/security_baseline.json`), 6 audit categories (network, packages, users, files, processes, malware), three-tier escalation (call/warning/clean). SQLite `security_audit_log` table. Heartbeat schedule: Sunday 7:00 AM. Commands: `/audit`, `/audit reset`, `/audit baseline`, `/audit ports`, `/audit packages`. Bootstrap installs ClamAV, chkrootkit, rkhunter automatically.

### Phase 19: Rename + GitHub Install ✅
MiniClaw renamed to **Kovo**. `ESAM_TELEGRAM_ID` → `OWNER_TELEGRAM_ID` for generic installs. Bootstrap v4.0 (16 steps) clones source from `github.com/Ava-AgentOne/kovo`, installs Python deps from `requirements.txt`, builds dashboard frontend via npm — no "build with Claude" step needed. Every friend gets identical code, dashboard, and logo. Kovo brand: #378ADD blue alien mascot with antennae and rosy cheeks.

## Environment Variables (.env)
```
# Telegram Bot
TELEGRAM_BOT_TOKEN=
OWNER_TELEGRAM_ID=

# Telegram Userbot (for voice calls — get from https://my.telegram.org)
TELEGRAM_API_ID=
TELEGRAM_API_HASH=

# Google Workspace
GOOGLE_CREDENTIALS_PATH=/opt/kovo/config/google-credentials.json

# Optional: ElevenLabs for premium TTS (default is edge-tts which is free)
# ELEVENLABS_API_KEY=
```

## Key Principles
1. **Self-evolving**: The agent can install packages, create services, and write new skills
2. **OpenClaw compatible**: Workspace files are interchangeable with OpenClaw
3. **Cost-efficient**: Ollama for simple tasks, Claude only when needed
4. **Safe**: Dangerous operations require Telegram confirmation from Esam
5. **Observable**: Everything logged to daily memory files
6. **Resilient**: Systemd service auto-restarts on crash
