"""Google auth-flow helpers (v3.0) — code extraction, no network."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.tools.google_api import extract_auth_code


class TestExtractAuthCode:
    def test_bare_code_passthrough(self):
        assert extract_auth_code("  4/0AXcode123  ") == "4/0AXcode123"

    def test_full_redirect_url(self):
        url = ("http://localhost:53682/?state=abc&iss=https://accounts.google.com"
               "&code=4/0AXtheRealCode&scope=https://www.googleapis.com/auth/drive")
        assert extract_auth_code(url) == "4/0AXtheRealCode"

    def test_url_without_code_falls_through(self):
        assert extract_auth_code("http://localhost:53682/?state=abc") == \
            "http://localhost:53682/?state=abc"
