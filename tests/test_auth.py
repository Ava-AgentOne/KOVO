"""
Dashboard auth tests — session signing, login request lifecycle, rate
limiting, and the require_auth guard.
Run: cd $KOVO_DIR && venv/bin/python -m pytest tests/ -v
"""
import sys
import time
from pathlib import Path

import pytest

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.dashboard import auth


@pytest.fixture(autouse=True)
def isolated_auth(tmp_path, monkeypatch):
    """Point auth storage at a temp dir and reset all module state."""
    monkeypatch.setattr(auth, "data_path", lambda: tmp_path)
    auth._secret_cache = None
    auth._sessions_cache = None
    auth._requests.clear()
    auth._last_request_by_ip.clear()
    yield


class TestSessions:
    def test_create_and_validate(self):
        cookie = auth.create_session("10.0.1.50")
        assert auth.validate_cookie(cookie) is not None

    def test_reject_garbage(self):
        assert auth.validate_cookie(None) is None
        assert auth.validate_cookie("") is None
        assert auth.validate_cookie("not.a.cookie") is None

    def test_reject_tampered_signature(self):
        cookie = auth.create_session("10.0.1.50")
        payload, sig = cookie.rsplit(".", 1)
        assert auth.validate_cookie(f"{payload}.{'0' * len(sig)}") is None

    def test_reject_tampered_expiry(self):
        cookie = auth.create_session("10.0.1.50")
        sid = cookie.split(".")[0]
        future = int(time.time()) + 999999999
        assert auth.validate_cookie(f"{sid}.{future}.{cookie.rsplit('.', 1)[1]}") is None

    def test_revoke(self):
        cookie = auth.create_session("10.0.1.50")
        sid = auth.validate_cookie(cookie)
        auth.revoke_session(sid)
        assert auth.validate_cookie(cookie) is None

    def test_expired_session_rejected(self):
        cookie = auth.create_session("10.0.1.50")
        sid = cookie.split(".")[0]
        auth._sessions()[sid]["expires"] = int(time.time()) - 10
        assert auth.validate_cookie(cookie) is None

    def test_persists_across_cache_reset(self):
        """Sessions survive a service restart (JSON on disk)."""
        cookie = auth.create_session("10.0.1.50")
        auth._sessions_cache = None  # simulate restart
        assert auth.validate_cookie(cookie) is not None

    def test_secret_file_permissions(self, tmp_path):
        auth.create_session("10.0.1.50")
        mode = (tmp_path / "dashboard_secret.key").stat().st_mode & 0o777
        assert mode == 0o600


class TestLoginRequests:
    def test_lifecycle_approved(self):
        req = auth.create_login_request("10.0.1.50")
        assert auth.get_request(req["request_id"])["status"] == "pending"
        assert auth.resolve_request(req["request_id"], approved=True)
        got = auth.consume_approved(req["request_id"])
        assert got is not None
        # one-shot: second consume fails
        assert auth.consume_approved(req["request_id"]) is None

    def test_lifecycle_denied(self):
        req = auth.create_login_request("10.0.1.50")
        assert auth.resolve_request(req["request_id"], approved=False)
        assert auth.get_request(req["request_id"])["status"] == "denied"
        assert auth.consume_approved(req["request_id"]) is None

    def test_unknown_request(self):
        assert not auth.resolve_request("nonexistent", approved=True)
        assert auth.get_request("nonexistent") is None

    def test_double_resolve_rejected(self):
        req = auth.create_login_request("10.0.1.50")
        assert auth.resolve_request(req["request_id"], approved=True)
        assert not auth.resolve_request(req["request_id"], approved=True)

    def test_expired_request_purged(self):
        req = auth.create_login_request("10.0.1.50")
        auth._requests[req["request_id"]]["created"] = time.time() - auth.REQUEST_TTL - 1
        assert auth.get_request(req["request_id"]) is None

    def test_code_format(self):
        req = auth.create_login_request("10.0.1.50")
        assert len(req["code"]) == 7 and req["code"][3] == "-"

    def test_per_ip_cooldown(self):
        auth.create_login_request("10.0.1.50")
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as e:
            auth.create_login_request("10.0.1.50")
        assert e.value.status_code == 429

    def test_max_pending(self):
        from fastapi import HTTPException
        for i in range(auth.MAX_PENDING_REQUESTS):
            auth.create_login_request(f"10.0.1.{i}")
        with pytest.raises(HTTPException) as e:
            auth.create_login_request("10.0.1.99")
        assert e.value.status_code == 429


class TestRequireAuth:
    def test_blocks_without_cookie(self, monkeypatch):
        import asyncio
        from fastapi import HTTPException
        from unittest.mock import MagicMock
        monkeypatch.setattr(auth, "is_configured", lambda: True)
        request = MagicMock()
        request.cookies = {}
        with pytest.raises(HTTPException) as e:
            asyncio.run(auth.require_auth(request=request))
        assert e.value.status_code == 401

    def test_allows_valid_cookie(self, monkeypatch):
        import asyncio
        from unittest.mock import MagicMock
        monkeypatch.setattr(auth, "is_configured", lambda: True)
        cookie = auth.create_session("10.0.1.50")
        request = MagicMock()
        request.cookies = {auth.COOKIE_NAME: cookie}
        assert asyncio.run(auth.require_auth(request=request)) is None

    def test_bypassed_when_unconfigured(self, monkeypatch):
        import asyncio
        from unittest.mock import MagicMock
        monkeypatch.setattr(auth, "is_configured", lambda: False)
        request = MagicMock()
        request.cookies = {}
        assert asyncio.run(auth.require_auth(request=request)) is None
