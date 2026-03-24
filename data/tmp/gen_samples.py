#!/usr/bin/env python3
"""
List English Female voices and generate audio samples for top 4.
Also sends them via Telegram.
"""
import subprocess
import sys
import os

# Step 1: List voices
print("=== Listing all English Female voices ===")
r = subprocess.run(
    ['/opt/miniclaw/venv/bin/edge-tts', '--list-voices'],
    capture_output=True, text=True
)
lines = r.stdout.strip().split('\n')
english_female = [l for l in lines if 'en-' in l and 'Female' in l]
print(f"Total voices found: {len(lines)}")
print(f"English Female voices: {len(english_female)}\n")
for v in english_female:
    print(v)

print("\n=== Generating samples for top 4 voices ===")

voices = [
    'en-US-AriaNeural',
    'en-US-JennyNeural',
    'en-US-MichelleNeural',
    'en-GB-SoniaNeural',
]

text = "Good morning Esam! This is your Kovo assistant. How can I help you today?"
audio_dir = '/opt/miniclaw/data/audio'

generated = []
for voice in voices:
    out_path = os.path.join(audio_dir, f'sample_{voice}.mp3')
    print(f"Generating: {voice} -> {out_path}")
    r = subprocess.run(
        ['/opt/miniclaw/venv/bin/edge-tts', '--voice', voice, '--text', text, '--write-media', out_path],
        capture_output=True, text=True
    )
    if r.returncode == 0 and os.path.exists(out_path):
        size = os.path.getsize(out_path)
        print(f"  OK: {size} bytes")
        generated.append((voice, out_path))
    else:
        print(f"  FAILED: {r.stderr}")

print(f"\n=== Generated {len(generated)}/{len(voices)} samples ===")

# Step 2: Send via Telegram
BOT_TOKEN = '8667608247:AAEDMpIyshdl0ae0zK7nFHhFRRezdtYOQdM'
CHAT_ID = '8339361967'

print("\n=== Sending via Telegram ===")

# Send intro message first
intro_r = subprocess.run([
    'curl', '-s', '-X', 'POST',
    f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',
    '-d', f'chat_id={CHAT_ID}',
    '-d', 'text=Here are 4 female voice samples — pick your favourite! 👇',
    '-d', 'parse_mode=Markdown'
], capture_output=True, text=True)
print(f"Intro message: {intro_r.stdout[:200]}")

# Send each voice sample
for voice, path in generated:
    print(f"Sending {voice}...")
    r = subprocess.run([
        'curl', '-s', '-X', 'POST',
        f'https://api.telegram.org/bot{BOT_TOKEN}/sendVoice',
        '-F', f'chat_id={CHAT_ID}',
        '-F', f'voice=@{path}',
        '-F', f'caption=🎙️ Voice: {voice}'
    ], capture_output=True, text=True)
    resp = r.stdout[:300]
    if '"ok":true' in resp:
        print(f"  Sent OK: {voice}")
    else:
        print(f"  Response: {resp}")

print("\nDone.")
print("\n=== Full list of English Female voices ===")
for v in english_female:
    print(v)
