"""Tests for the MCP OAuth client (v3.1 — the Store that signs in)."""
import base64
import hashlib
import json
import time
from unittest.mock import MagicMock, patch

import pytest

from src.tools import mcp_oauth


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("KOVO_DIR", str(tmp_path))
    (tmp_path / "data").mkdir()
    mcp_oauth._pending.clear()
    yield


def _mock_http(get_map=None, post_map=None):
    """httpx.Client mock: url-prefix → (status, json) for get/post."""
    def make_resp(status, body):
        r = MagicMock()
        r.is_success = 200 <= status < 300
        r.status_code = status
        r.json.return_value = body
        r.text = json.dumps(body)[:200]
        return r

    client = MagicMock()
    def _lookup(mapping, url):
        for prefix, (status, body) in (mapping or {}).items():
            if url.startswith(prefix):
                return make_resp(status, body)
        return make_resp(404, {})
    client.get.side_effect = lambda url, **kw: _lookup(get_map, url)
    client.post.side_effect = lambda url, **kw: _lookup(post_map, url)
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=client)
    cm.__exit__ = MagicMock(return_value=False)
    return patch.object(mcp_oauth.httpx, "Client", return_value=cm), client


AS_META = {
    "authorization_endpoint": "https://auth.example.com/authorize",
    "token_endpoint": "https://auth.example.com/token",
    "registration_endpoint": "https://auth.example.com/register",
}


# ── PKCE ──────────────────────────────────────────────────────────────────────

def test_pkce_challenge_is_s256_of_verifier():
    verifier, challenge = mcp_oauth._pkce_pair()
    expect = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    assert challenge == expect and len(verifier) >= 43


# ── Discovery ─────────────────────────────────────────────────────────────────

def test_discover_via_protected_resource_metadata():
    ctx, _ = _mock_http(get_map={
        "https://mcp.example.com/.well-known/oauth-protected-resource":
            (200, {"resource": "https://mcp.example.com/x/mcp",
                   "authorization_servers": ["https://auth.example.com"]}),
        "https://auth.example.com/.well-known/oauth-authorization-server":
            (200, AS_META),
    })
    with ctx:
        meta = mcp_oauth.discover("https://mcp.example.com/x/mcp")
    assert meta["token_endpoint"] == AS_META["token_endpoint"]
    assert meta["resource"] == "https://mcp.example.com/x/mcp"


def test_discover_falls_back_to_origin_as_issuer():
    ctx, _ = _mock_http(get_map={
        "https://mcp.example.com/.well-known/oauth-authorization-server":
            (200, AS_META),
    })
    with ctx:
        meta = mcp_oauth.discover("https://mcp.example.com/mcp")
    assert meta["authorization_endpoint"] == AS_META["authorization_endpoint"]


def test_discover_raises_readable_error_when_nothing_found():
    ctx, _ = _mock_http()
    with ctx, pytest.raises(ValueError, match="discovered"):
        mcp_oauth.discover("https://mcp.example.com/mcp")


# ── Registration ──────────────────────────────────────────────────────────────

def _meta(reg="https://auth.example.com/register"):
    return {"issuer": "https://auth.example.com",
            "registration_endpoint": reg,
            "token_endpoint": "https://auth.example.com/token"}


def test_register_client_success_missing_endpoint_and_reuse():
    ctx, client = _mock_http(post_map={
        "https://auth.example.com/register": (201, {"client_id": "cid-1"}),
    })
    with ctx:
        out = mcp_oauth.register_client(_meta(), "http://kovo/cb")
    assert out["client_id"] == "cid-1"
    sent = client.post.call_args.kwargs["json"]
    assert sent["redirect_uris"] == ["http://kovo/cb"]
    assert "refresh_token" in sent["grant_types"]

    # Second call must reuse the cached registration — no second POST
    ctx2, client2 = _mock_http(post_map={})
    with ctx2:
        again = mcp_oauth.register_client(_meta(), "http://kovo/cb")
    assert again["client_id"] == "cid-1"
    client2.post.assert_not_called()

    # An UNCACHED issuer with no registration endpoint must refuse
    # (the cached issuer above would legitimately skip registration)
    other = {"issuer": "https://other.example.com",
             "registration_endpoint": None,
             "token_endpoint": "https://other.example.com/token"}
    with pytest.raises(ValueError, match="registration"):
        mcp_oauth.register_client(other, "http://kovo/cb")


# ── start_connect / complete_connect ─────────────────────────────────────────

def _start(server="way"):
    ctx, _ = _mock_http(
        get_map={
            "https://mcp.example.com/.well-known/oauth-protected-resource":
                (200, {"resource": "https://mcp.example.com/mcp",
                       "authorization_servers": ["https://auth.example.com"]}),
            "https://auth.example.com/.well-known/oauth-authorization-server":
                (200, AS_META),
        },
        post_map={
            "https://auth.example.com/register": (201, {"client_id": "cid-1"}),
        })
    with ctx:
        url = mcp_oauth.start_connect(server, "https://mcp.example.com/mcp",
                                      "http://kovo/cb")
    return url


def test_start_connect_builds_authorize_url_with_pkce_and_resource():
    import urllib.parse
    url = _start()
    q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    assert q["code_challenge_method"] == ["S256"]
    assert q["resource"] == ["https://mcp.example.com/mcp"]
    assert q["state"][0] in mcp_oauth._pending


def test_complete_connect_exchanges_and_persists():
    import urllib.parse
    url = _start("way")
    state = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)["state"][0]
    ctx, client = _mock_http(post_map={
        "https://auth.example.com/token":
            (200, {"access_token": "at-1", "refresh_token": "rt-1",
                   "expires_in": 3600}),
    })
    with ctx:
        server = mcp_oauth.complete_connect(state, "the-code")
    assert server == "way" and mcp_oauth.has_token("way")
    sent = client.post.call_args.kwargs["data"]
    assert sent["code"] == "the-code" and sent["code_verifier"]
    # single-use state
    with pytest.raises(ValueError):
        mcp_oauth.complete_connect(state, "the-code")


def test_get_access_token_fresh_expired_and_absent():
    store = {"servers": {"way": {"access_token": "at-1", "refresh_token": "rt-1",
                     "expires_at": time.time() + 3600,
                     "token_endpoint": "https://auth.example.com/token",
                     "client_id": "cid-1", "resource": "r"}}}
    mcp_oauth._save_store(store)
    assert mcp_oauth.get_access_token("way") == "at-1"
    assert mcp_oauth.get_access_token("nope") is None

    store["servers"]["way"]["expires_at"] = time.time() - 10
    mcp_oauth._save_store(store)
    ctx, client = _mock_http(post_map={
        "https://auth.example.com/token":
            (200, {"access_token": "at-2", "refresh_token": "rt-2",
                   "expires_in": 3600}),
    })
    with ctx:
        assert mcp_oauth.get_access_token("way") == "at-2"
    assert client.post.call_args.kwargs["data"]["grant_type"] == "refresh_token"
    # rotation persisted
    assert mcp_oauth._load_store()["servers"]["way"]["refresh_token"] == "rt-2"


def test_refresh_rejection_returns_none():
    store = {"servers": {"way": {"access_token": "at-1", "refresh_token": "rt-1",
                     "expires_at": time.time() - 10,
                     "token_endpoint": "https://auth.example.com/token",
                     "client_id": "cid-1", "resource": "r"}}}
    mcp_oauth._save_store(store)
    ctx, _ = _mock_http(post_map={
        "https://auth.example.com/token": (400, {"error": "invalid_grant"}),
    })
    with ctx:
        assert mcp_oauth.get_access_token("way") is None


# ── Injection into the brain's MCP config ────────────────────────────────────

def test_external_servers_skips_unconnected_and_injects_token(monkeypatch):
    from src.agents import mcp_config
    entry = {"enabled": True, "type": "http",
             "url": "https://mcp.example.com/mcp", "auth": "oauth"}
    with patch.object(mcp_config, "_to_sdk_config",
                      return_value={"type": "http",
                                    "url": entry["url"]}) as _:
        # no token yet → skipped
        assert mcp_config.sdk_config_with_auth("way", entry) is None
        # token present → Authorization injected
        mcp_oauth._save_store({"servers": {"way": {
            "access_token": "at-9", "refresh_token": None,
            "expires_at": time.time() + 3600,
            "token_endpoint": "t", "client_id": "c", "resource": "r"}},
            "clients": {}})
        sdk = mcp_config.sdk_config_with_auth("way", entry)
    assert sdk["headers"]["Authorization"] == "Bearer at-9"


def test_token_store_file_is_private(tmp_path):
    mcp_oauth._save_store({"servers": {"x": {"access_token": "s"}}, "clients": {}})
    assert (mcp_oauth._store_path().stat().st_mode & 0o777) == 0o600


# ── Review-driven hardening ───────────────────────────────────────────────────

def test_discover_oidc_path_appended_variant():
    # Keycloak/Cognito style: issuer has a path; metadata ONLY at
    # {issuer}/.well-known/openid-configuration
    ctx, _ = _mock_http(get_map={
        "https://mcp.example.com/.well-known/oauth-protected-resource":
            (200, {"resource": "https://mcp.example.com/mcp",
                   "authorization_servers": ["https://kc.example.com/realms/r1"]}),
        "https://kc.example.com/realms/r1/.well-known/openid-configuration":
            (200, AS_META),
    })
    with ctx:
        meta = mcp_oauth.discover("https://mcp.example.com/mcp")
    assert meta["token_endpoint"] == AS_META["token_endpoint"]


def test_discover_rejects_non_http_authorization_endpoint():
    evil = dict(AS_META, authorization_endpoint="javascript:alert(1)")
    ctx, _ = _mock_http(get_map={
        "https://mcp.example.com/.well-known/oauth-authorization-server":
            (200, evil),
    })
    with ctx, pytest.raises(ValueError, match="invalid"):
        mcp_oauth.discover("https://mcp.example.com/mcp")


def test_discover_foreign_resource_falls_back_to_mcp_url():
    ctx, _ = _mock_http(get_map={
        "https://mcp.example.com/.well-known/oauth-protected-resource":
            (200, {"resource": "https://evil.example.net/other",
                   "authorization_servers": ["https://auth.example.com"]}),
        "https://auth.example.com/.well-known/oauth-authorization-server":
            (200, AS_META),
    })
    with ctx:
        meta = mcp_oauth.discover("https://mcp.example.com/mcp")
    assert meta["resource"] == "https://mcp.example.com/mcp"


def test_token_withheld_when_entry_url_changed():
    mcp_oauth._save_store({"servers": {"way": {
        "access_token": "at-1", "refresh_token": None, "expires_at": None,
        "mcp_url": "https://mcp.example.com/mcp",
        "token_endpoint": "t", "client_id": "c", "resource": "r"}},
        "clients": {}})
    assert mcp_oauth.get_access_token(
        "way", mcp_url="https://mcp.example.com/mcp") == "at-1"
    assert mcp_oauth.get_access_token(
        "way", mcp_url="https://evil.example.net/mcp") is None


def test_no_expiry_token_never_refreshed():
    mcp_oauth._save_store({"servers": {"way": {
        "access_token": "at-1", "refresh_token": None, "expires_at": None,
        "token_endpoint": "t", "client_id": "c", "resource": "r"}},
        "clients": {}})
    # No httpx mock: any network call would blow up — none may happen
    assert mcp_oauth.get_access_token("way") == "at-1"
