# Sub-Agent Registry

This file lists all active sub-agents created by Kovo.
The main agent (Kovo) handles everything by default.
Sub-agents are created on demand when Esam approves a recommendation.

## Main Agent
- **Name**: Kovo
- **SOUL**: /opt/kovo/workspace/SOUL.md
- **Tools**: all (shell, browser, google_api, telegram_call, tts, ollama, claude_cli, whisper)
- **Status**: active

## Sub-Agents

<!-- Sub-agents are added here automatically when created.
Format:
### {name}
- **SOUL**: workspace/agents/{name}/SOUL.md
- **Tools**: [list of tool names]
- **Memory**: workspace/agents/{name}/memory/
- **Created**: YYYY-MM-DD
- **Purpose**: one-line description
-->

*No sub-agents yet. Kovo will recommend one when it notices repeated specialised requests.*

## Sub-Agent Creation Flow
1. Kovo notices Esam repeatedly asks for a specific type of job
2. Kovo recommends creating a sub-agent via Telegram message
3. Esam replies "yes" or "/create_agent {name}"
4. Kovo creates workspace/agents/{name}/ with SOUL.md, tools.yaml, memory/
5. Kovo registers it in this file
6. Sub-agent is live — Kovo delegates to it and summarises results
