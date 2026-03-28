---
tools:
- config_needed: null
  description: Execute shell commands on the VM (file ops, installs, services)
  install_command: null
  name: shell
  status: configured
- config_needed: null
  description: Playwright headless browser automation (scraping, screenshots, web
    interaction)
  install_command: playwright install chromium
  name: browser
  status: configured
- config_needed: null
  description: Google Docs, Drive, and Gmail integration via OAuth2
  install_command: null
  name: google_api
  status: configured
- config_needed: null
  description: Telegram voice calls + voice messages via Pyrogram userbot
  install_command: null
  name: telegram_call
  status: configured
- config_needed: null
  description: Text-to-speech using edge-tts (Microsoft voices, free)
  install_command: pip install edge-tts
  name: tts
  status: configured
- config_needed: null
  description: "Ollama LLM on NUC at <OLLAMA-HOST>:11434 \u2014 used for heartbeat checks"
  install_command: null
  name: ollama
  status: configured
- config_needed: null
  description: Claude Code CLI subprocess for complex reasoning (Sonnet/Opus)
  install_command: npm install -g @anthropic-ai/claude-code
  name: claude_cli
  status: configured
- config_needed: null
  description: Groq Whisper cloud transcription with local Whisper fallback
  install_command: pip install openai-whisper --no-deps && pip install torch --index-url
    https://download.pytorch.org/whl/cpu
  name: whisper
  status: configured
- config_needed: null
  description: GitHub repos, issues, pull requests, file management, and code search
    via PyGithub
  install_command: pip install PyGithub
  name: github
  status: configured
---

# Tool Registry

This file tracks all tools available to Kovo and its sub-agents.
Agents check this registry before using a tool and notify the owner if a tool is missing or unconfigured.

## Status Values
- `installed` — tool is installed and ready to use
- `not_installed` — tool needs to be installed (`install_command` tells how)
- `configured` — tool is installed and fully configured
- `not_configured` — tool is installed but needs configuration (`config_needed` tells what)

## Environment
- **OS**: Ubuntu 25.10 (Questing) — VM on Unraid (8GB RAM, 50GB disk)
- **Python**: 3.13 (venv at /opt/kovo/venv)
- **Node**: 22+ (system install)
- **Workspace**: /opt/kovo/workspace

## Network Hosts
- **Ollama**: http://<OLLAMA-HOST>:11434
- **Home Assistant**: (configure when ready)
- **Unraid WebUI**: (configure when ready)

## Tool Notes
- **shell**: Always available. Dangerous commands require the owner's Telegram confirmation.
- **browser**: Playwright with Chromium in headless mode.
- **google_api**: Requires OAuth2. Run `/auth_google` in Telegram to configure.
- **telegram_call**: Pyrogram userbot. Falls back to voice message if call not answered.
- **tts**: edge-tts (Microsoft Azure voices, free). Voice: en-US-AriaNeural.
- **ollama**: Runs on NUC. Used only for scheduled heartbeat health checks.
- **claude_cli**: Uses the owner's Claude Max subscription. No API key needed.
- **whisper**: Groq whisper-large-v3-turbo (primary) + local Whisper (fallback).
- **github**: PyGithub. Set GITHUB_TOKEN in config/.env. Run `/auth_github` to verify.
