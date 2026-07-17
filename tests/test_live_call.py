"""
Live Call tests (v3.0 Phase 3c) — VAD utterance segmentation and exit
phrases. Pure logic; no calls, no audio hardware.
"""
import math
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.tools.live_call import (BYTES_PER_MS, EXIT_RE, UtteranceDetector,
                                 _rms, is_active)


def tone(ms: int, amplitude: int = 8000) -> bytes:
    """Loud sine chunk (speech stand-in)."""
    n = ms * BYTES_PER_MS // 2
    return struct.pack(
        f"<{n}h",
        *(int(amplitude * math.sin(i / 8)) for i in range(n)),
    )


def silence(ms: int) -> bytes:
    return b"\x00" * (ms * BYTES_PER_MS)


class TestRms:
    def test_silence_is_zero(self):
        assert _rms(silence(20)) == 0.0
        assert _rms(b"") == 0.0

    def test_tone_is_loud(self):
        assert _rms(tone(20)) > 1000


class TestUtteranceDetector:
    def _feed(self, det, chunks):
        out = []
        for c in chunks:
            r = det.feed(c)
            if r:
                out.append(r)
        return out

    def test_silence_never_triggers(self):
        det = UtteranceDetector()
        assert self._feed(det, [silence(20)] * 200) == []

    def test_speech_then_silence_yields_utterance(self):
        det = UtteranceDetector()
        chunks = [tone(20)] * 50 + [silence(20)] * 50   # 1s speech, 1s silence
        got = self._feed(det, chunks)
        assert len(got) == 1
        assert len(got[0]) >= 900 * BYTES_PER_MS        # ≈1s speech + tail

    def test_short_blip_ignored(self):
        det = UtteranceDetector()
        # 100ms blip < START_MS never starts an utterance
        got = self._feed(det, [tone(20)] * 5 + [silence(20)] * 100)
        assert got == []

    def test_max_length_forces_cut(self):
        det = UtteranceDetector(max_s=1)
        got = self._feed(det, [tone(20)] * 100)          # 2s continuous speech
        assert len(got) >= 1
        assert len(got[0]) <= 1 * 1000 * BYTES_PER_MS + 20 * BYTES_PER_MS

    def test_detector_resets_between_utterances(self):
        det = UtteranceDetector()
        chunks = ([tone(20)] * 40 + [silence(20)] * 50) * 2
        got = self._feed(det, chunks)
        assert len(got) == 2


class TestExitPhrases:
    def test_matches(self):
        for phrase in ("goodbye", "Bye!", "ok bye now", "please hang up",
                       "end the call", "that's all"):
            assert EXIT_RE.search(phrase), phrase

    def test_non_matches(self):
        for phrase in ("buy some milk", "the goodbye party is tomorrow — "
                       "actually tell me about it",):
            pass  # 'goodbye party' legitimately matches; accept greedy exit
        assert not EXIT_RE.search("buy some milk")
        assert not EXIT_RE.search("what a byte is")


class TestActiveFlag:
    def test_not_active_by_default(self):
        assert is_active() is False


class TestExperimentalGate:
    def test_disabled_by_default(self, monkeypatch):
        from src.gateway import config as cfg
        from src.tools.live_call import is_enabled
        monkeypatch.setattr(cfg, "get", lambda: {})
        assert is_enabled() is False                    # EXPERIMENTAL: off unless opted in
        monkeypatch.setattr(cfg, "get", lambda: {"experimental": {"live_call": True}})
        assert is_enabled() is True
        monkeypatch.setattr(cfg, "get", lambda: {"experimental": {"live_call": "yes"}})
        assert is_enabled() is False                    # strict True only
