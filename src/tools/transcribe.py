"""
Speech-to-text transcription.

Primary:  Groq API (whisper-large-v3-turbo) — fast, cloud, ~1 s turnaround.
Fallback: Local Whisper (faster-whisper or openai-whisper) — no API key needed.

Usage:
    t = Transcriber(groq_api_key="gsk_your_api_key_here")
    text = await t.transcribe("/path/to/audio.mp3")
"""
from __future__ import annotations

import asyncio
import logging
import subprocess
from functools import partial
from pathlib import Path
from src.utils.platform import kovo_dir

import httpx

log = logging.getLogger(__name__)

_AUDIO_DIR = Path(str(kovo_dir()) + "/data/audio")
_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

_GROQ_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
_GROQ_MODEL = "whisper-large-v3-turbo"


class Transcriber:
    """
    Transcribes audio files to text.
    Tries Groq first; falls back to local Whisper on any failure.
    """

    def __init__(self, groq_api_key: str = "", whisper_model: str = "base", language: str = "en"):
        self.groq_api_key = groq_api_key
        self.whisper_model = whisper_model
        self.language = language
        self._whisper_instance = None  # lazy-loaded

    # ── public entry point ────────────────────────────────────────────────────

    async def transcribe(self, audio_path: str) -> str:
        """
        Transcribe audio_path to text.
        audio_path should be an MP3 (convert with ffmpeg before calling).
        Returns the transcribed text string.
        """
        if self.groq_api_key:
            try:
                text = await self.groq_transcribe(audio_path)
                log.info("Groq transcription: %d chars", len(text))
                return text
            except Exception as e:
                log.warning("Groq transcription failed (%s), falling back to local Whisper", e)

        return await self.whisper_transcribe(audio_path)

    # ── Groq cloud transcription ──────────────────────────────────────────────

    async def groq_transcribe(self, audio_path: str) -> str:
        """
        POST audio_path to the Groq Whisper API.
        Expects an MP3 file. Returns the transcribed text.
        Raises on any HTTP or network error.
        """
        audio_path = str(audio_path)
        async with httpx.AsyncClient(timeout=30) as client:
            with open(audio_path, "rb") as f:
                response = await client.post(
                    _GROQ_URL,
                    headers={"Authorization": f"Bearer {self.groq_api_key}"},
                    data={"model": _GROQ_MODEL, "language": self.language},
                    files={"file": (Path(audio_path).name, f, "audio/mpeg")},
                )
            response.raise_for_status()
            return response.json()["text"].strip()

    # ── local Whisper fallback ────────────────────────────────────────────────

    async def whisper_transcribe(self, audio_path: str) -> str:
        """
        Transcribe using local faster-whisper or openai-whisper.
        Converts to 16 kHz mono WAV first for maximum compatibility.
        Runs in a thread executor so the event loop stays unblocked.
        """
        src = Path(audio_path)
        wav_path = src.with_suffix(".wav")

        proc = subprocess.run(
            [
                "ffmpeg", "-y", "-i", str(src),
                "-ar", "16000", "-ac", "1", "-f", "wav", str(wav_path),
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"ffmpeg WAV conversion failed: {proc.stderr[:300]}")

        loop = asyncio.get_event_loop()
        text = await loop.run_in_executor(
            None, partial(self._transcribe_sync, str(wav_path))
        )
        return text

    def _load_whisper(self):
        if self._whisper_instance is not None:
            return self._whisper_instance
        try:
            from faster_whisper import WhisperModel
            self._whisper_instance = WhisperModel(
                self.whisper_model, device="cpu", compute_type="int8"
            )
            log.info("Loaded faster-whisper '%s'", self.whisper_model)
        except ImportError:
            import whisper as _whisper
            self._whisper_instance = _whisper.load_model(self.whisper_model)
            log.info("Loaded openai-whisper '%s'", self.whisper_model)
        return self._whisper_instance

    def _transcribe_sync(self, wav_path: str) -> str:
        model = self._load_whisper()
        try:
            from faster_whisper import WhisperModel
            if isinstance(model, WhisperModel):
                segments, _ = model.transcribe(wav_path, beam_size=5, language=self.language)
                return " ".join(s.text.strip() for s in segments).strip()
        except ImportError:
            pass
        result = model.transcribe(wav_path, language=self.language)
        return result["text"].strip()
