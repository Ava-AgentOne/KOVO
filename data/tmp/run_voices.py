#!/usr/bin/env python3
"""
List English Female edge-tts voices, generate 4 samples, send via Telegram.
Usage: python3 run_voices.py
"""
import asyncio
import os
import subprocess
import sys

# Add venv to path
sys.path.insert(0, '/opt/miniclaw/venv/lib/python3.13/site-packages')

import edge_tts

BOT_TOKEN = '8667608247:AAEDMpIyshdl0ae0zK7nFHhFRRezdtYOQdM'
CHAT_ID = '8339361967'
AUDIO_DIR = '/opt/miniclaw/data/audio'
SAMPLE_TEXT = "Good morning Esam! This is your Kovo assistant. How can I help you today?"

TOP_4_VOICES = [
    'en-US-AriaNeural',
    'en-US-JennyNeural',
    'en-US-MichelleNeural',
    'en-GB-SoniaNeural',
]


async def list_english_female_voices():
    voices = await edge_tts.list_voices()
    female_en = [
        v for v in voices
        if v.get('Locale', '').startswith('en-') and v.get('Gender', '') == 'Female'
    ]
    return female_en


async def generate_sample(voice_name, output_path, text):
    communicate = edge_tts.Communicate(text, voice_name)
    await communicate.save(output_path)


def send_telegram_message(token, chat_id, text):
    r = subprocess.run([
        'curl', '-s', '-X', 'POST',
        f'https://api.telegram.org/bot{token}/sendMessage',
        '-d', f'chat_id={chat_id}',
        '-d', f'text={text}',
        '-d', 'parse_mode=Markdown'
    ], capture_output=True, text=True, timeout=30)
    return r.stdout


def send_telegram_voice(token, chat_id, file_path, caption):
    r = subprocess.run([
        'curl', '-s', '-X', 'POST',
        f'https://api.telegram.org/bot{token}/sendVoice',
        '-F', f'chat_id={chat_id}',
        '-F', f'voice=@{file_path}',
        '-F', f'caption={caption}'
    ], capture_output=True, text=True, timeout=60)
    return r.stdout


async def main():
    # Step 1: List all English Female voices
    print("Fetching voice list from Microsoft...")
    female_voices = await list_english_female_voices()
    print(f"\nFound {len(female_voices)} English Female voices:\n")
    for v in female_voices:
        print(f"  {v['ShortName']}  ({v['Locale']})  -  {v.get('FriendlyName', '')}")

    # Step 2: Generate samples for top 4
    print(f"\nGenerating samples for top 4 voices...")
    generated = []
    for voice in TOP_4_VOICES:
        out_path = os.path.join(AUDIO_DIR, f'sample_{voice}.mp3')
        print(f"  Generating {voice}...")
        try:
            await generate_sample(voice, out_path, SAMPLE_TEXT)
            size = os.path.getsize(out_path)
            print(f"    OK: {size:,} bytes -> {out_path}")
            generated.append((voice, out_path))
        except Exception as e:
            print(f"    FAILED: {e}")

    # Step 3: Send intro message
    print(f"\nSending Telegram intro message...")
    resp = send_telegram_message(
        BOT_TOKEN, CHAT_ID,
        "Here are 4 female voice samples — pick your favourite! 👇"
    )
    if '"ok":true' in resp:
        print("  Intro message sent OK")
    else:
        print(f"  Response: {resp[:300]}")

    # Step 4: Send each voice sample
    for voice, path in generated:
        print(f"  Sending voice sample: {voice}...")
        resp = send_telegram_voice(BOT_TOKEN, CHAT_ID, path, f"🎙️ Voice: {voice}")
        if '"ok":true' in resp:
            print(f"    Sent OK")
        else:
            print(f"    Response: {resp[:300]}")

    print("\n=== Done ===")
    print(f"Sent {len(generated)}/{len(TOP_4_VOICES)} voice samples to Telegram chat {CHAT_ID}")

    return female_voices


if __name__ == '__main__':
    asyncio.run(main())
