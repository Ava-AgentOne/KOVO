import subprocess
r = subprocess.run(['/opt/miniclaw/venv/bin/edge-tts', '--list-voices'], capture_output=True, text=True)
lines = r.stdout.strip().split('\n')
english_female = [l for l in lines if 'en-' in l and 'Female' in l]
print(f"Total voices: {len(lines)}")
print(f"English Female voices: {len(english_female)}")
for v in english_female:
    print(v)
