"""Voice-note reply shaping (v3.0 Phase 3a) — speakable() text for TTS."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.telegram.formatting import speakable


class TestSpeakable:
    def test_markdown_stripped(self):
        out = speakable("**Server** is `healthy` — see [the dashboard](http://x/y).\n- CPU fine\n## Details")
        assert "*" not in out and "`" not in out and "[" not in out and "#" not in out
        assert "Server is healthy" in out
        assert "the dashboard" in out          # link label kept, URL gone
        assert "http" not in out

    def test_code_blocks_omitted(self):
        out = speakable("Run this:\n```bash\nrm -rf /tmp/x\n```\nDone.")
        assert "rm -rf" not in out
        assert "(code omitted)" in out

    def test_bare_urls_replaced(self):
        assert "a link" in speakable("Check https://example.com/very/long/path now")

    def test_cap_with_graceful_ending(self):
        out = speakable("word " * 500)
        assert len(out) <= 850
        assert out.endswith("full details in the text reply.")

    def test_emoji_removed(self):
        assert speakable("Done ✅ 🎉 all good") == "Done all good"
