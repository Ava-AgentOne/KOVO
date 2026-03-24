"""
Text-to-Speech engine with multiple backends.
Default: edge-tts (free, Microsoft Azure voices)
Optional: piper (local), elevenlabs (premium)
"""
from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)

_AUDIO_DIR = Path("/opt/miniclaw/data/audio")
_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

# Default voices per backend
_DEFAULT_VOICES = {
    "edge-tts": "en-US-GuyNeural",
    "piper": "en_US-lessac-medium",
    "elevenlabs": "Josh",
}


class TTSEngine:
    def __init__(
        self,
        backend: str = "edge-tts",
        voice: str | None = None,
        elevenlabs_api_key: str | None = None,
    ):
        self.backend = backend
        self.voice = voice or _DEFAULT_VOICES.get(backend, "en-US-GuyNeural")
        self.elevenlabs_api_key = elevenlabs_api_key or os.environ.get("ELEVENLABS_API_KEY")

    async def speak(self, text: str, output_path: str | None = None) -> str:
        """
        Generate speech from text.
        Returns absolute path to the generated MP3 file.
        """
        if output_path is None:
            output_path = str(_AUDIO_DIR / "tts_output.mp3")

        if self.backend == "edge-tts":
            return await self._edge_tts(text, output_path)
        elif self.backend == "piper":
            return await self._piper(text, output_path)
        elif self.backend == "elevenlabs":
            return await self._elevenlabs(text, output_path)
        else:
            raise ValueError(f"Unknown TTS backend: {self.backend}")

    async def speak_to_raw(self, text: str, output_path: str | None = None) -> str:
        """
        Generate speech and convert to RAW PCM (48kHz mono s16le) for tgcalls.
        Returns path to the .raw file.

        Note: prefer speak() + passing the MP3 directly to MediaStream when
        using py-tgcalls v2+, which decodes encoded audio natively.
        """
        mp3_path = await self.speak(text, output_path)
        raw_path = mp3_path.replace(".mp3", ".raw").replace(".wav", ".raw")
        if not raw_path.endswith(".raw"):
            raw_path += ".raw"

        result = subprocess.run(
            [
                "ffmpeg", "-y", "-i", mp3_path,
                "-f", "s16le", "-ac", "1", "-ar", "48000",
                "-acodec", "pcm_s16le", raw_path,
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg conversion failed: {result.stderr[:300]}")
        return raw_path

    async def _edge_tts(self, text: str, output_path: str) -> str:
        import edge_tts
        communicate = edge_tts.Communicate(text, self.voice)
        await communicate.save(output_path)
        log.debug("edge-tts generated: %s", output_path)
        return output_path

    async def _piper(self, text: str, output_path: str) -> str:
        """Piper TTS — runs piper binary as subprocess."""
        wav_path = output_path.replace(".mp3", ".wav")
        model_dir = Path("/opt/miniclaw/data/piper-models")
        model_file = next(model_dir.glob("*.onnx"), None) if model_dir.exists() else None

        if not model_file:
            log.warning("No piper model found, falling back to edge-tts")
            return await self._edge_tts(text, output_path)

        result = subprocess.run(
            ["piper", "--model", str(model_file), "--output_file", wav_path],
            input=text,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"piper failed: {result.stderr[:200]}")

        # Convert wav to mp3
        subprocess.run(
            ["ffmpeg", "-y", "-i", wav_path, output_path],
            capture_output=True,
        )
        return output_path

    async def _elevenlabs(self, text: str, output_path: str) -> str:
        """ElevenLabs API — premium TTS."""
        if not self.elevenlabs_api_key:
            raise RuntimeError("ELEVENLABS_API_KEY not set")
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice}",
                headers={"xi-api-key": self.elevenlabs_api_key},
                json={"text": text, "model_id": "eleven_monolingual_v1"},
                timeout=60,
            )
            resp.raise_for_status()
            Path(output_path).write_bytes(resp.content)
        return output_path
