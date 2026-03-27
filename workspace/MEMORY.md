# MEMORY.md

## Long-term Memory

## Communication Style Preferences
- Esam wants ALL replies formatted with rich Telegram markdown: bold, italic, code blocks, bullet points, emojis
- Use every available Telegram formatting tool to make messages visually beautiful
- Always include relevant emojis throughout the message
- **Voice messages must always include the text content as well** — never send audio-only
- **Voice reply only when Esam sends a voice message** — text replies get text only, no TTS
- Default TTS voice: en-US-AriaNeural (chosen 2026-03-24)

## System Knowledge
- Ollama runs on NUC at 10.0.1.212:11434 with llama3.1:8b
- Kovo VM is on Unraid with 8GB RAM, 50GB disk
- Esam previously used OpenClaw and wants the same experience at lower cost
- PyTorch runs in CPU-only mode (no GPU in VM)


## 2026-03-22
Here are 3-5 key learnings from today's log:

* The user is interacting with a chatbot or AI assistant named Kovo, which responds to the user's queries using the Miniclaw model and Claude/Sonnet agent.
* The user has asked Kovo to call them on Telegram, but Kovo does not recognize this command as a valid skill (Session 10:48-10:55).
* Kovo is able to provide information about disk space usage on the system, including a formatted report with emojis (Sessions 12:09 and 12:11).
* The user has asked Kovo to use more creative and visually appealing responses in Telegram, which Kovo is willing to do (Session 12:11).


## 2026-03-22
Here are today's key learnings from the log:

- 🎙️ **Voice preference set** — Default TTS voice changed from `GuyNeural` to `en-US-AriaNeural` (natural & expressive), chosen by Esam from 4 samples

- 📢 **Reply format rule established** — Every reply must include **both** voice 🔊 + text 📝, always. Initially misinterpreted as "voice messages only need text," then clarified to mean *all* replies

- 🖼️ **Image capability confirmed** — Kovo *can* send images to Telegram by: searching the web → downloading to VM → using `bot.send_photo()`. Sandbox was blocking it at the time, but the path is viable

- ⚠️ **Bot code needs updating** — The voice+text-on-every-reply behaviour requires a code change to the Kovo bot handler; memory/preferences alone won't enforce it automatically

- 💥 **Error at 13:24** — `claude -p` exited with code 143 (SIGTERM / timeout kill), causing a failed session. Worth monitoring for recurrence


## 2026-03-22
Here are today's key learnings:

- 🎙️ **TTS voice selected** — Esam picked `en-US-AriaNeural` as the default voice after sampling 4 options; `GuyNeural` was the old default

- 🔄 **Voice reply rule changed twice** — First set to "always send voice + text," then walked back to **"voice reply only when Esam sends a voice message"** — text messages get text-only replies. Code in `bot.py` was updated to match

- 🖼️ **Image sending implemented** — Code written to support web image search + `bot.send_photo()` delivery to Telegram. Requires `duckduckgo-search` pip install + service restart to activate

- 💥 **Error at 13:24** — `claude -p` exited with code 143 (SIGTERM/timeout). One-off so far, but worth watching

- ✅ **Bot already had voice+text logic** — When "always send voice" was requested, the bot code already supported it. The final preference flip to voice-only-on-voice-input required an actual code removal


## 2026-03-24
- [preference] Esam wants local weather (Al Ain, UAE) included in the morning briefing


## 2026-03-24
- [tool] Weather data fetched from wttr.in (no API key required), returns compact format with emoji, temperature, and feels-like


## 2026-03-24
Here are today's key learnings:

- 🌤️ **Weather added to morning briefing** — `fetch_weather()` integrated into `src/heartbeat/checks.py`, pulling Al Ain data from `wttr.in` (no API key needed)

- 📋 **Full command list reviewed** — Esam browsed all available commands; useful reference for onboarding or docs updates

- 🎙️ **Voice weather briefing delivered** — Esam requested a call with the weather briefing; delivered as a voice message (Al Ain: ⛅ 27°C, 48% humidity, ~30 km/h wind on Tue 24 Mar)

- 💬 **Light activity day** — Only 4 sessions, no errors or system alerts; system running healthy


## 2026-03-24
Here are today's key learnings from the agent log:

- 🔧 **Telegram call bug fixed** — Two issues in `telegram_call.py`: wrong status name for detecting answered calls + a related logic error. Fix is in place; this was a bug in the original implementation, not something introduced by Esam.

- 💚 **System is healthy** — Health report sent to email: RAM at 21%, CPU ~5%, disk usage within normal range. Score: 90/100.

- 📞 **Wake-up call confirmed working** — Test call rang for 30 seconds, then correctly fell back to a voice message (13 sec). The call + fallback flow is functioning end-to-end.

- 🎙️ **Default TTS voice changed to `en-US-AriaNeural`** — Esam sampled 4 female voices and picked Aria (US American accent). Config and memory updated; all future calls will use this voice.

- 🌅 **Weather added to morning briefing** — `fetch_weather()` integrated into `checks.py` pulling Al Ain data from `wttr.in` (no API key needed). Delivered as a voice message: ⛅ 27°C, 48% humidity, ~30 km/h wind.


## 2026-03-24
- [decision] Esam chose `en-US-AriaNeural` as the default TTS voice for all future calls and voice messages


## 2026-03-24
- [project] Telegram voice call bug fixed in `telegram_call.py` — wrong status name (`ACCEPTED_CALL` doesn't exist in py-tgcalls v2) caused calls to never detect answer; fix is in source


## 2026-03-24
- [tool] Voice call fallback to voice message works correctly — tested and confirmed delivering 13-sec audio when call goes unanswered after 30 seconds


## 2026-03-24
- [preference] Esam prefers health reports sent to his email, not just Telegram


## 2026-03-24
- [project] Kovo successfully sent a health report via email (system scored 90/100, all metrics green)


## 2026-03-26
Not much to extract today — very light activity:

- 💬 **Two brief check-ins only** — Esam said "hi" at 05:30 and 07:20, no tasks or requests made
- 🤖 **Both sessions used claude/sonnet** — no Ollama routing or sub-agent delegation triggered
- ✅ **System responding normally** — bot replied correctly to both messages, no errors logged


## 2026-03-26
- [project] Security audit triggered twice in quick succession (10:33 and 10:36) for executable files in /tmp and /dev/shm — system was found clean both times


## 2026-03-26
- [decision] Auto-extract memory log format confirmed working — Kovo correctly identified light-activity days with only brief check-ins


## 2026-03-26
- [project] /dev/shm was empty during security scan; /tmp had one executable file that was flagged but cleared as legitimate
