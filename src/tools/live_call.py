"""
Kovo Live Call (v3.0 Phase 3c) — two-way voice conversation during a call.

Turn loop: Kovo rings the owner → greeting → LISTEN (energy-based VAD
segments an utterance from the 24 kHz PCM the call delivers) → Whisper
transcription → agent turn (fast model, its own persistent session) →
speech-shaped TTS played back into the call → LISTEN again.

Exit: the owner says goodbye ("bye", "goodbye", "hang up", "end call"),
hangs up, stays silent through two prompts, or the 10-minute cap hits.

Proven by the 2026-07-16 echo harness: pytgcalls.record() delivers
AudioQuality.LOW (24 kHz mono s16le) frames while play() handles the
outbound direction — full duplex, mode switches per turn.

One call at a time; the reminder-call path checks is_active() and falls
back to a voice message rather than fighting over the userbot session.
"""
from __future__ import annotations

import asyncio
import logging
import re
import wave

from src.utils.platform import data_path

log = logging.getLogger(__name__)

RATE = 24000                    # AudioQuality.LOW = (24000, 1), s16le
BYTES_PER_MS = RATE * 2 // 1000

SPEECH_RMS = 600                # energy gate (tune per handset/mic)
START_MS = 240                  # speech this long → utterance started
END_MS = 800                    # silence this long → utterance finished
MAX_UTTERANCE_S = 20
SILENCE_PROMPT_S = 45           # quiet this long → "are you still there?"
CALL_CAP_S = 600                # hard stop
EXIT_RE = re.compile(r"\b(good\s?bye|bye|hang\s?up|end (the )?call|that's all)\b", re.I)

_active = asyncio.Lock()


def is_active() -> bool:
    return _active.locked()


def is_enabled() -> bool:
    """EXPERIMENTAL feature gate — settings.yaml experimental.live_call,
    default OFF (v1 latency is walkie-talkie class; owner opts in)."""
    from src.gateway import config as cfg
    exp = cfg.get().get("experimental") or {}
    return exp.get("live_call", False) is True


def _rms(pcm: bytes) -> float:
    """RMS of s16le PCM — pure python, fast enough for 20 ms chunks."""
    if not pcm:
        return 0.0
    import array
    samples = array.array("h", pcm[: len(pcm) - (len(pcm) % 2)])
    if not samples:
        return 0.0
    acc = 0
    for s in samples:
        acc += s * s
    return (acc / len(samples)) ** 0.5


class UtteranceDetector:
    """Feed PCM chunks; returns a complete utterance when one ends.
    Pure logic — unit tested without audio hardware."""

    def __init__(self, speech_rms: float = SPEECH_RMS, start_ms: int = START_MS,
                 end_ms: int = END_MS, max_s: int = MAX_UTTERANCE_S):
        self.speech_rms = speech_rms
        self.start_ms = start_ms
        self.end_ms = end_ms
        self.max_bytes = max_s * 1000 * BYTES_PER_MS
        self.reset()

    def reset(self) -> None:
        self._buf = bytearray()
        self._speech_ms = 0
        self._silence_ms = 0
        self._started = False

    def feed(self, pcm: bytes) -> bytes | None:
        """Returns the finished utterance's PCM, or None if still listening."""
        ms = len(pcm) // BYTES_PER_MS
        loud = _rms(pcm) >= self.speech_rms

        if not self._started:
            if loud:
                self._speech_ms += ms
                self._buf.extend(pcm)
                if self._speech_ms >= self.start_ms:
                    self._started = True
                    self._silence_ms = 0
            else:
                # pre-speech: keep a short rolling tail for a natural onset
                self._speech_ms = 0
                self._buf.extend(pcm)
                if len(self._buf) > 500 * BYTES_PER_MS:
                    del self._buf[: len(self._buf) - 500 * BYTES_PER_MS]
            return None

        self._buf.extend(pcm)
        if loud:
            self._silence_ms = 0
        else:
            self._silence_ms += ms

        if self._silence_ms >= self.end_ms or len(self._buf) >= self.max_bytes:
            out = bytes(self._buf)
            self.reset()
            return out
        return None


class LiveCallSession:
    USER_NS = -70001            # brain session namespace for live calls

    def __init__(self, agent, transcriber, owner_id: int,
                 api_id: int, api_hash: str):
        self.agent = agent
        self.transcriber = transcriber
        self.owner_id = owner_id
        self.api_id = api_id
        self.api_hash = api_hash
        self.audio_dir = data_path() / "audio"
        self.audio_dir.mkdir(parents=True, exist_ok=True)

    async def _tts(self, text: str, name: str) -> str:
        path = str(self.audio_dir / name)
        await self.agent.tts.speak(text, path)
        return path

    def _write_wav(self, pcm: bytes, name: str) -> str:
        path = str(self.audio_dir / name)
        with wave.open(path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(RATE)
            w.writeframes(pcm)
        return path

    async def _pcm_to_mp3(self, pcm: bytes) -> str:
        """The Transcriber contract is MP3 (the voice-note path feeds it MP3
        too) — WAV made Groq reject and the local-whisper fallback choke."""
        import subprocess
        wav = self._write_wav(pcm, "lc_utterance.wav")
        mp3 = str(self.audio_dir / "lc_utterance.mp3")

        def _convert():
            r = subprocess.run(
                ["ffmpeg", "-y", "-i", wav, "-ar", "16000", "-q:a", "4", mp3],
                capture_output=True, text=True, timeout=30,
            )
            if r.returncode != 0:
                raise RuntimeError(f"ffmpeg mp3 conversion failed: {r.stderr[-200:]}")

        await asyncio.get_event_loop().run_in_executor(None, _convert)
        return mp3

    async def run(self) -> dict:
        """Place the call and hold the conversation. Returns a summary."""
        if _active.locked():
            return {"ok": False, "error": "a live call is already active"}
        async with _active:
            try:
                return await self._run_inner()
            except Exception as e:
                log.error("Live call failed: %s", e, exc_info=True)
                return {"ok": False, "error": str(e)[:200]}

    async def _run_inner(self) -> dict:
        from pyrogram import Client
        from pytgcalls import PyTgCalls
        from pytgcalls.types import (AudioQuality, CallConfig, ChatUpdate,
                                     MediaStream, RecordStream, StreamEnded,
                                     StreamFrames)

        app = Client("kovo_caller", workdir=str(data_path()),
                     api_id=self.api_id, api_hash=self.api_hash)
        calls = PyTgCalls(app)

        detector = UtteranceDetector()
        utterances: asyncio.Queue[bytes] = asyncio.Queue()
        listening = asyncio.Event()
        played_done = asyncio.Event()
        ended = asyncio.Event()
        got_media = asyncio.Event()

        @calls.on_update()
        async def _on_update(_, update):
            if isinstance(update, StreamFrames):
                got_media.set()
                if listening.is_set():
                    for f in update.frames:
                        done = detector.feed(f.frame)
                        if done:
                            await utterances.put(done)
            elif isinstance(update, StreamEnded):
                played_done.set()
            elif isinstance(update, ChatUpdate):
                s = str(getattr(update, "status", "")).upper()
                if "LEFT" in s or "DISCARDED" in s or "CLOSED" in s:
                    ended.set()

        # Instant acknowledgments: pre-generated once, played the moment an
        # utterance ends — masks STT+brain latency so the line never goes dead.
        fillers = []
        for i, phrase in enumerate(("Mm-hmm.", "One moment.", "Let me check.")):
            try:
                fillers.append(await self._tts(phrase, f"lc_filler{i}.mp3"))
            except Exception:
                pass

        async def ack(n: int) -> None:
            if fillers:
                try:
                    await calls.play(self.owner_id,
                                     MediaStream(fillers[n % len(fillers)]),
                                     CallConfig())
                except Exception:
                    pass

        async def say(text: str, name: str) -> None:
            """Speak into the call; listening pauses while Kovo talks."""
            listening.clear()
            detector.reset()
            mp3 = await self._tts(text, name)
            played_done.clear()
            await calls.play(self.owner_id, MediaStream(mp3), CallConfig())
            try:
                await asyncio.wait_for(played_done.wait(), timeout=90)
            except asyncio.TimeoutError:
                pass
            listening.set()

        turns = 0
        log.info("Live call: ringing owner %s", self.owner_id)
        await calls.start()
        try:
            await calls.record(
                self.owner_id,
                RecordStream(audio=True, audio_parameters=AudioQuality.LOW),
                CallConfig(),
            )
            try:
                await asyncio.wait_for(got_media.wait(), timeout=45)
            except asyncio.TimeoutError:
                log.info("Live call: unanswered")
                return {"ok": False, "error": "unanswered"}

            await say("Hello Esam, Kovo here. What can I do for you? "
                      "Say goodbye whenever you're done.", "lc_greet.mp3")

            start = asyncio.get_event_loop().time()
            silent_prompts = 0
            while not ended.is_set():
                if asyncio.get_event_loop().time() - start > CALL_CAP_S:
                    await say("We've hit the ten minute limit — let's continue "
                              "in chat. Goodbye!", "lc_cap.mp3")
                    break
                try:
                    pcm = await asyncio.wait_for(
                        utterances.get(), timeout=SILENCE_PROMPT_S)
                except asyncio.TimeoutError:
                    silent_prompts += 1
                    if silent_prompts >= 2:
                        await say("I'll let you go. Goodbye!", "lc_bye.mp3")
                        break
                    await say("Are you still there?", "lc_still.mp3")
                    continue

                silent_prompts = 0
                import time as _time
                t0 = _time.monotonic()
                listening.clear()          # stop capturing while we process
                await ack(turns)           # instant "mm-hmm" — no dead air
                try:
                    mp3_in = await self._pcm_to_mp3(pcm)
                    text = (await self.transcriber.transcribe(mp3_in) or "").strip()
                except Exception as e:
                    log.warning("Live call transcription failed: %s", e)
                    await say("Sorry, I didn't catch that.", "lc_miss.mp3")
                    continue
                t_stt = _time.monotonic() - t0
                if not text:
                    listening.set()
                    continue
                log.info("Live call heard: %r", text[:100])

                if EXIT_RE.search(text):
                    await say("Alright, goodbye Esam!", "lc_bye.mp3")
                    break

                turns += 1
                t1 = _time.monotonic()
                try:
                    result = await self.agent.handle(
                        message=(
                            "(live phone call — answer in 1-3 short spoken "
                            f"sentences, no markdown) {text}"
                        ),
                        user_id=self.USER_NS,
                        force_complexity="simple",
                    )
                    reply = result.get("text", "I'm not sure.")
                except Exception as e:
                    log.error("Live call agent turn failed: %s", e)
                    reply = "Sorry, I hit a snag with that one."

                t_brain = _time.monotonic() - t1
                t2 = _time.monotonic()
                from src.telegram.formatting import speakable
                await say(speakable(reply, cap=600), "lc_reply.mp3")
                log.info("Live call turn %d timing: stt=%.1fs brain=%.1fs "
                         "tts+play=%.1fs total=%.1fs", turns, t_stt, t_brain,
                         _time.monotonic() - t2, _time.monotonic() - t0)

            return {"ok": True, "turns": turns}
        finally:
            try:
                await calls.leave_call(self.owner_id)
            except Exception:
                pass
            await asyncio.sleep(1)
            try:
                await app.stop()
            except Exception:
                pass
            log.info("Live call ended (%d turns)", turns)
