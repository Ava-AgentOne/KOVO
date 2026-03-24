---
name: phone-call
description: Place real Telegram voice calls to Esam with TTS audio, or send voice messages
tools: [telegram_call, tts]
trigger: call, voice call, ring, phone, urgent call, speak to me, talk to me, voice message, call me, tgcall
---

# Phone Call Skill

## Capabilities
- **Real Telegram calls**: Places actual voice calls using the MiniClaw userbot account
- **TTS audio**: Converts text to speech (edge-tts, Microsoft voices)
- **Voice message fallback**: If call not answered in 30s, sends a voice message instead
- **Urgency levels**: Normal (voice message) vs Urgent (attempt call first)

## When to Use
- Esam explicitly asks to be called (`/call` command)
- Agent marks a notification as URGENT (disk full, service down, security alert)
- Scheduled wake-up reminders

## TTS Voices
- Default: `en-US-GuyNeural` (Microsoft, good quality, free)
- Arabic: `ar-AE-HamdanNeural` for Arabic messages
- Female: `en-US-JennyNeural`

## Procedures

### Place Urgent Call
1. Generate TTS audio for the message
2. Attempt Telegram call via userbot
3. Play audio when answered
4. If no answer after 30s → send voice message via bot

### Session Health Check
The userbot session is checked every 6 hours. If expired, Esam is alerted via bot with reauth instructions.

## Setup
Requires a second Telegram account with credentials in `.env`:
- `TELEGRAM_API_ID` and `TELEGRAM_API_HASH` from https://my.telegram.org
- Run `/reauth_caller` to authenticate the userbot account
