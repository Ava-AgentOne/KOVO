# KOVO Architecture

KOVO is a self-hosted AI agent powered by Claude Code. This document explains how the system works.

## System Overview

```mermaid
flowchart TD
    subgraph User["User"]
        TG["📱 Telegram"]
        DASH["🖥️ Dashboard"]
    end

    subgraph Gateway["Gateway (FastAPI)"]
        BOT["Telegram Bot\npython-telegram-bot"]
        WS["WebSocket\n/api/ws/chat"]
        API["REST API\n/api/*"]
    end

    subgraph Brain["AI Brain"]
        KOVO_AGENT["KovoAgent\nsingle main agent"]
        ROUTER["Smart Router\nsonnet / opus"]
        CLAUDE["Claude Code CLI\nclaude -p"]
    end

    subgraph Memory["Memory"]
        SOUL["SOUL.md\npersonality"]
        USER_MD["USER.md\nowner profile"]
        MEM["MEMORY.md\npinned + learnings"]
        DAILY["Daily Logs\nmemory/YYYY-MM-DD.md"]
        DB[("SQLite\nkovo.db")]
    end

    subgraph Tools["Tools & Skills"]
        SHELL["Shell"]
        BROWSER["Browser"]
        GOOGLE["Google API"]
        TTS_TOOL["TTS + Calls"]
        SEARCH["Web Search"]
        SKILLS["Skills\n(SKILL.md)"]
    end

    TG -->|messages| BOT
    DASH -->|WebSocket| WS
    DASH -->|HTTP| API
    BOT --> KOVO_AGENT
    WS --> KOVO_AGENT
    KOVO_AGENT --> ROUTER
    ROUTER --> CLAUDE
    KOVO_AGENT -->|reads| SOUL
    KOVO_AGENT -->|reads| USER_MD
    KOVO_AGENT -->|reads/writes| MEM
    KOVO_AGENT -->|writes| DAILY
    KOVO_AGENT -->|queries| DB
    CLAUDE -->|uses| SHELL
    CLAUDE -->|uses| BROWSER
    CLAUDE -->|uses| GOOGLE
    KOVO_AGENT -->|loads| SKILLS

    style TG fill:#26A5E4,color:#fff,stroke:none
    style DASH fill:#378ADD,color:#fff,stroke:none
    style KOVO_AGENT fill:#378ADD,color:#fff,stroke:none
    style CLAUDE fill:#DA7756,color:#fff,stroke:none
    style DB fill:#10b981,color:#fff,stroke:none
```

## Message Flow

When you send a message to KOVO, here's what happens:

```mermaid
sequenceDiagram
    participant User
    participant Bot as Telegram Bot
    participant Agent as KovoAgent
    participant Router as Smart Router
    participant Claude as Claude Code

    User->>Bot: "What's my disk usage?"
    
    Note over Bot: Auto web search?<br/>URL detection?<br/>Intercept tags?
    
    Bot->>Agent: handle(message)
    Agent->>Agent: build_system_prompt()<br/>keyword scan → load relevant context
    Agent->>Router: route(message, system_prompt)
    Router->>Router: classify complexity
    Router->>Claude: claude -p (sonnet or opus)
    Claude->>Claude: Execute shell commands,<br/>reason about results
    Claude-->>Router: Response text
    Router-->>Agent: {text, model_used}
    Agent->>Agent: persist to daily log
    Agent-->>Bot: Response
    
    Note over Bot: Parse [SEND_IMAGE],<br/>[SET_REMINDER],<br/>[MAKE_CALL] tags
    
    Bot-->>User: Formatted reply
```

## Smart Context Loading

KOVO doesn't load everything into every prompt. It uses keyword matching to load only what's needed:

```mermaid
flowchart TD
    MSG["Incoming Message"] --> ALWAYS["Always Loaded\nSOUL.md + USER.md\n+ Pinned Memory"]
    MSG --> SCAN{"Keyword Scan\n(pure Python)"}
    
    SCAN -->|"remember, decided,\nprefer, history"| LEARNINGS["Learnings\nfrom MEMORY.md"]
    SCAN -->|"today, yesterday,\nrecent, morning"| LOGS["Daily Logs"]
    SCAN -->|"tool, install,\nconfigure, setup"| TOOLS_CTX["TOOLS.md"]
    SCAN -->|"health, cpu,\nram, disk"| HB["HEARTBEAT.md"]
    SCAN -->|"database, query,\ntable, stats"| SCHEMA["DB Schema"]
    SCAN -->|"call, browser,\nsecurity, report"| SKILL["Best Matching\nSkill"]
    SCAN -->|"nothing matched"| FALLBACK["Fallback:\nLearnings + TOOLS.md"]

    style ALWAYS fill:#10b981,color:#fff,stroke:none
    style SCAN fill:#378ADD,color:#fff,stroke:none
    style FALLBACK fill:#f59e0b,color:#fff,stroke:none
```

This saves **60-90% of system prompt tokens** on routine messages.

## Tag System

The agent communicates actions to the bot through tags in its response text:

| Tag | Action | Example |
|---|---|---|
| `[SEND_IMAGE: query]` | Search and send a photo | `[SEND_IMAGE: sunset over Dubai]` |
| `[SET_REMINDER: msg \| time \| delivery]` | Create a reminder | `[SET_REMINDER: Call dentist \| 2026-04-02T15:00 \| message]` |
| `[MAKE_CALL: message]` | Place a voice call | `[MAKE_CALL: Good morning, your disk is 90% full]` |

The bot layer parses these tags, executes the action, and strips them from the visible response.

## Memory System

```mermaid
flowchart TD
    subgraph Always["Always in Brain"]
        PINNED["Pinned Memory\nkey-value facts\ntimezone, city, preferences"]
    end

    subgraph OnDemand["Loaded on Demand"]
        LEARN["Learnings\nrolling log of insights"]
        DAILY_LOG["Daily Logs\nmemory/YYYY-MM-DD.md"]
    end

    subgraph Extraction["Daily at 11 PM"]
        EXTRACT["Auto-Extractor\n1 Claude Sonnet call/day"]
    end

    DAILY_LOG -->|"input (3200 char cap)"| EXTRACT
    EXTRACT -->|"key-value pairs"| PINNED
    EXTRACT -->|"bullet points"| LEARN
    LEARN -->|"archived when >500 lines"| ARCHIVE["Archive"]

    style PINNED fill:#10b981,color:#fff,stroke:none
    style EXTRACT fill:#378ADD,color:#fff,stroke:none
    style ARCHIVE fill:#6b7280,color:#fff,stroke:none
```

## Heartbeat System

5 scheduled jobs run automatically via APScheduler:

| Schedule | Job | Description |
|---|---|---|
| Daily 3:00 AM | Archive logs | Move daily logs older than 30 days |
| Daily 11:00 PM | Auto-extract | Extract learnings from today's log |
| Sunday 3:30 AM | Consolidation | Archive learnings if >500 lines |
| Daily 10:00 AM | Version check | Check GitHub for new releases |
| Every 60 seconds | Reminders | Fire due reminders (message/call) |

## Security Layers

```mermaid
flowchart LR
    subgraph External["External"]
        ENV["Token Masking\nin all logs"]
        PERM[".env chmod 600"]
        HOOK["Pre-push Hook\nblocks credentials"]
    end

    subgraph API["API Layer"]
        META["Shell Metachar\nBlocking"]
        KEYS["Env Key\nWhitelist (9 keys)"]
        PATH["Path Traversal\nProtection"]
    end

    subgraph Claude["Claude Code"]
        SANDBOX["Sandbox\n61-entry allowlist"]
        APPROVE["Runtime Approval\nvia Telegram"]
    end

    style ENV fill:#10b981,color:#fff,stroke:none
    style META fill:#10b981,color:#fff,stroke:none
    style SANDBOX fill:#10b981,color:#fff,stroke:none
```

## Project Structure

```
<KOVO_DIR>/                  # /opt/kovo (Linux) or ~/.kovo (macOS)
├── src/
│   ├── gateway/             # FastAPI app, config, routes
│   ├── telegram/            # Bot, commands, formatting
│   ├── agents/              # KovoAgent + sub-agent runner  
│   ├── memory/              # Pinned + Learnings + SQLite
│   ├── tools/               # Shell, browser, calls, search, etc.
│   ├── skills/              # Skill registry + loader
│   ├── heartbeat/           # APScheduler jobs
│   ├── router/              # Smart model router
│   ├── onboarding/          # First-run 5-question flow
│   ├── utils/               # platform.py, tz.py
│   └── dashboard/           # React + Vite + Tailwind
├── workspace/
│   ├── SOUL.md              # Agent personality
│   ├── USER.md              # Owner profile
│   ├── MEMORY.md            # Pinned + Learnings
│   ├── memory/              # Daily logs
│   └── skills/              # SKILL.md per skill
├── config/                  # .env, settings.yaml
├── data/                    # kovo.db, security, backups
├── scripts/                 # update.sh, backup.sh, restore.sh
└── bootstrap.sh             # One-line installer
```

## Cross-Platform

All paths flow through `src/utils/platform.py`. No source file hardcodes `/opt/kovo`.

| Platform | Install Path | Service | Package Manager |
|---|---|---|---|
| Linux | `/opt/kovo` | systemd | apt |
| macOS | `~/.kovo` | launchd | Homebrew |

The `KOVO_DIR` environment variable overrides auto-detection on any platform.
