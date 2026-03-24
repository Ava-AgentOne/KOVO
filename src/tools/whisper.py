"""
Whisper speech-to-text transcription.

Uses faster-whisper if installed (faster, lower memory), falls back to
openai-whisper. The model is lazy-loaded on first transcription call so
startup is not delayed.
"""
from __future__ import annotations

import asyncio
import logging
import subprocess
from functools import partial
from pathlib import Path

log = logging.getLogger(__name__)

_AUDIO_DIR = Path("/opt/miniclaw/data/audio")
_AUDIO_DIR.mkdir(parents=True, exist_ok=True)


class WhisperTranscriber:
    def __init__(self, model: str = "base"):
        self.model = model
        self._instance = None   # lazy-loaded

    # ── model loading ─────────────────────────────────────────────────────────

    def _load(self):
        if self._instance is not None:
            return self._instance
        try:
            from faster_whisper import WhisperModel
            self._instance = WhisperModel(self.model, device="cpu", compute_type="int8")
            log.info("Loaded faster-whisper model '%s'", self.model)
        except ImportError:
            import whisper as _whisper
            self._instance = _whisper.load_model(self.model)
            log.info("Loaded openai-whisper model '%s'", self.model)
        return self._instance

    # ── internal sync transcription (runs in executor) ────────────────────────

    def _transcribe_sync(self, wav_path: str) -> str:
        model = self._load()
        try:
            from faster_whisper import WhisperModel
            if isinstance(model, WhisperModel):
                segments, _ = model.transcribe(wav_path, beam_size=5)
                return " ".join(s.text.strip() for s in segments).strip()
        except ImportError:
            pass
        # openai-whisper
        result = model.transcribe(wav_path)
        return result["text"].strip()

    # ── public API ────────────────────────────────────────────────────────────

    async def transcribe(self, audio_path: str) -> str:
        """
        Transcribe an audio file (OGG, MP3, WAV, …) to text.
        Converts to 16 kHz mono WAV before passing to Whisper for reliability.
        Returns the transcribed text string.
        """
        src = Path(audio_path)
        wav_path = src.with_suffix(".wav")

        # ffmpeg → 16 kHz mono WAV (Whisper's native preference)
        proc = subprocess.run(
            [
                "ffmpeg", "-y", "-i", str(src),
                "-ar", "16000", "-ac", "1", "-f", "wav", str(wav_path),
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"ffmpeg conversion failed: {proc.stderr[:300]}")

        loop = asyncio.get_event_loop()
        text = await loop.run_in_executor(None, partial(self._transcribe_sync, str(wav_path)))
        return text
