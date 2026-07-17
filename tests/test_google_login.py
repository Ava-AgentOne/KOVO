"""Tests for the dashboard's Google OAuth login (auth_api google endpoints)."""
import time
import urllib.parse
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.dashboard import auth, auth_api


GOOGLE_ENV = {
    "GOOGLE_CLIENT_ID": "cid-123",
    "GOOGLE_CLIENT_SECRET": "csecret-456",
    "GOOGLE_ALLOWED_EMAIL": "Owner@Example.com",
}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("KOVO_DIR", str(tmp_path))
    monkeypatch.delenv("GOOGLE_REDIRECT_URI", raising=False)
    (tmp_path / "config").mkdir()
    (tmp_path / "data").mkdir()
    auth._sessions_cache = None
    auth_api._google_states.clear()
    app = FastAPI()
    app.include_router(auth_api.router)
    return TestClient(app, follow_redirects=False)


def _mock_google(email="owner@example.com", verified=True,
                 token_ok=True, userinfo_ok=True):
    """Patch httpx.AsyncClient for the token-exchange + userinfo calls."""
    token_resp = MagicMock()
    token_resp.is_success = token_ok
    token_resp.json.return_value = {"access_token": "at-xyz"}
    token_resp.text = "token error body"

    user_resp = MagicMock()
    user_resp.is_success = userinfo_ok
    profile = {"email": email}
    if verified is not None:
        profile["verified_email"] = verified
    user_resp.json.return_value = profile
    user_resp.text = "userinfo error body"

    mock_client = AsyncMock()
    mock_client.post.return_value = token_resp
    mock_client.get.return_value = user_resp
    mock_client.__aenter__.return_value = mock_client
    return patch.object(auth_api.httpx, "AsyncClient",
                        return_value=mock_client), mock_client


def _seed_state(state="st-1", created=None):
    auth_api._google_states[state] = {
        "redirect_uri": "http://testserver/api/auth/google/callback",
        "created": created if created is not None else time.time(),
    }


# ── /google/login ─────────────────────────────────────────────────────────────

def test_login_redirects_to_google(client, monkeypatch):
    for k, v in GOOGLE_ENV.items():
        monkeypatch.setenv(k, v)
    r = client.get("/api/auth/google/login")
    assert r.status_code == 307 or r.status_code == 302
    loc = r.headers["location"]
    assert loc.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    q = urllib.parse.parse_qs(urllib.parse.urlparse(loc).query)
    assert q["client_id"] == ["cid-123"]
    assert q["scope"] == ["openid email"]
    state = q["state"][0]
    assert state in auth_api._google_states


@pytest.mark.parametrize("missing", ["GOOGLE_CLIENT_ID",
                                     "GOOGLE_CLIENT_SECRET",
                                     "GOOGLE_ALLOWED_EMAIL"])
def test_login_partial_config_refuses(client, monkeypatch, missing):
    # No hardcoded fallback: ANY missing var must refuse before Google
    for k, v in GOOGLE_ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.delenv(missing, raising=False)
    r = client.get("/api/auth/google/login")
    assert r.status_code == 302
    assert r.headers["location"] == "/dashboard/login?error=google_unconfigured"
    assert not auth_api._google_states


def test_login_prunes_expired_and_caps_states(client, monkeypatch):
    for k, v in GOOGLE_ENV.items():
        monkeypatch.setenv(k, v)
    _seed_state("expired", created=time.time() - 700)
    for i in range(120):
        _seed_state(f"s{i}")
    client.get("/api/auth/google/login")
    assert "expired" not in auth_api._google_states
    assert len(auth_api._google_states) <= 101  # cap + the new one


# ── /google/callback ──────────────────────────────────────────────────────────

def test_callback_consent_denied(client):
    r = client.get("/api/auth/google/callback?error=access_denied")
    assert r.status_code == 302
    assert r.headers["location"] == "/dashboard/login?error=google_denied"


def test_callback_unknown_state(client):
    r = client.get("/api/auth/google/callback?state=nope&code=c")
    assert r.status_code == 302
    assert r.headers["location"] == "/dashboard/login?error=google_state"


def test_callback_expired_state(client):
    _seed_state("old", created=time.time() - 700)
    r = client.get("/api/auth/google/callback?state=old&code=c")
    assert r.status_code == 302
    assert r.headers["location"] == "/dashboard/login?error=google_state"


def test_callback_state_single_use(client, monkeypatch):
    for k, v in GOOGLE_ENV.items():
        monkeypatch.setenv(k, v)
    _seed_state("once")
    ctx, _ = _mock_google()
    with ctx:
        client.get("/api/auth/google/callback?state=once&code=c")
    # Second use of the same state must fail regardless of outcome
    r = client.get("/api/auth/google/callback?state=once&code=c")
    assert r.headers["location"] == "/dashboard/login?error=google_state"


def test_callback_success_sets_year_cookie(client, monkeypatch):
    for k, v in GOOGLE_ENV.items():
        monkeypatch.setenv(k, v)
    _seed_state()
    ctx, mock_client = _mock_google(email="OWNER@example.com")
    with ctx:
        r = client.get("/api/auth/google/callback?state=st-1&code=auth-code")
    assert r.status_code == 302 and r.headers["location"] == "/dashboard/"
    cookie = r.headers.get("set-cookie", "")
    assert auth.COOKIE_NAME in cookie
    assert f"Max-Age={365 * 24 * 3600}" in cookie
    assert "HttpOnly" in cookie
    # The signed cookie must validate as a real session
    value = cookie.split(f"{auth.COOKIE_NAME}=")[1].split(";")[0]
    assert auth.validate_cookie(urllib.parse.unquote(value))
    # And the code we passed must be what was exchanged
    assert mock_client.post.call_args.kwargs["data"]["code"] == "auth-code"


def test_callback_wrong_email_forbidden(client, monkeypatch):
    for k, v in GOOGLE_ENV.items():
        monkeypatch.setenv(k, v)
    _seed_state()
    ctx, _ = _mock_google(email="intruder@example.com")
    with ctx:
        r = client.get("/api/auth/google/callback?state=st-1&code=c")
    assert r.headers["location"] == "/dashboard/login?error=google_forbidden"
    assert "set-cookie" not in r.headers


@pytest.mark.parametrize("verified", [False, None])  # None = field absent
def test_callback_unverified_email_forbidden(client, monkeypatch, verified):
    for k, v in GOOGLE_ENV.items():
        monkeypatch.setenv(k, v)
    _seed_state()
    ctx, _ = _mock_google(email="owner@example.com", verified=verified)
    with ctx:
        r = client.get("/api/auth/google/callback?state=st-1&code=c")
    assert r.headers["location"] == "/dashboard/login?error=google_forbidden"


def test_callback_token_exchange_failure(client, monkeypatch):
    for k, v in GOOGLE_ENV.items():
        monkeypatch.setenv(k, v)
    _seed_state()
    ctx, _ = _mock_google(token_ok=False)
    with ctx:
        r = client.get("/api/auth/google/callback?state=st-1&code=c")
    assert r.headers["location"] == "/dashboard/login?error=google_error"


def test_callback_network_error(client, monkeypatch):
    for k, v in GOOGLE_ENV.items():
        monkeypatch.setenv(k, v)
    _seed_state()
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.post.side_effect = httpx.ConnectTimeout("boom")
    with patch.object(auth_api.httpx, "AsyncClient", return_value=mock_client):
        r = client.get("/api/auth/google/callback?state=st-1&code=c")
    assert r.headers["location"] == "/dashboard/login?error=google_error"


# ── auth.create_session ttl ───────────────────────────────────────────────────

def test_create_session_custom_ttl(tmp_path, monkeypatch):
    monkeypatch.setenv("KOVO_DIR", str(tmp_path))
    (tmp_path / "data").mkdir()
    auth._sessions_cache = None
    cookie = auth.create_session("1.2.3.4", ttl=60)
    sid = auth.validate_cookie(cookie)
    assert sid
    expires = auth._sessions()[sid]["expires"]
    assert abs(expires - (time.time() + 60)) < 5

# ── /methods + redirect override ──────────────────────────────────────────────

def test_methods_reports_google_availability(client, monkeypatch):
    for k in GOOGLE_ENV:
        monkeypatch.delenv(k, raising=False)
    assert client.get("/api/auth/methods").json() == {
        "telegram": True, "google": False}
    for k, v in GOOGLE_ENV.items():
        monkeypatch.setenv(k, v)
    assert client.get("/api/auth/methods").json()["google"] is True


def test_redirect_uri_override_used(client, monkeypatch):
    for k, v in GOOGLE_ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("GOOGLE_REDIRECT_URI",
                       "https://kovo.example.ts.net/api/auth/google/callback")
    r = client.get("/api/auth/google/login")
    q = urllib.parse.parse_qs(urllib.parse.urlparse(r.headers["location"]).query)
    assert q["redirect_uri"] == [
        "https://kovo.example.ts.net/api/auth/google/callback"]
    # And the callback exchanges with the SAME stored URI
    state = q["state"][0]
    ctx, mock_client = _mock_google()
    with ctx:
        client.get(f"/api/auth/google/callback?state={state}&code=c")
    assert mock_client.post.call_args.kwargs["data"]["redirect_uri"] == \
        "https://kovo.example.ts.net/api/auth/google/callback"
