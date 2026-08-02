"""Tests for the Store guardrails (v3.0.1): registry auth flag + probe."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.dashboard.routers import mcp as mcp_router


@pytest.fixture()
def client():
    app = FastAPI()
    app.include_router(mcp_router.router)
    app.dependency_overrides[mcp_router.require_auth] = lambda: None
    return TestClient(app)


# ── auth_undeclared flag on normalized registry remotes ───────────────────────

def _registry_item(headers=None):
    return {"server": {
        "name": "io.example/gmail", "title": "Gmail", "version": "1.0",
        "description": "d",
        "remotes": [{"type": "streamable-http",
                     "url": "https://example.com/mcp",
                     **({"headers": headers} if headers else {})}],
    }}


def test_remote_without_headers_flagged():
    out = mcp_router._normalize_registry_entry(_registry_item())
    assert out["auth_undeclared"] is True


def test_remote_with_declared_header_not_flagged():
    out = mcp_router._normalize_registry_entry(_registry_item(
        headers=[{"name": "Authorization", "isRequired": True, "isSecret": True}]))
    assert out["auth_undeclared"] is False
    assert "Authorization" in out["headers"]


# ── /api/mcp/registry/probe ───────────────────────────────────────────────────

def _mock_stream(status, www=None, exc=None):
    resp = MagicMock()
    resp.status_code = status
    resp.headers = {"www-authenticate": www} if www else {}
    stream_cm = AsyncMock()
    stream_cm.__aenter__.return_value = resp
    http_client = MagicMock()
    if exc:
        http_client.stream = MagicMock(side_effect=exc)
    else:
        http_client.stream = MagicMock(return_value=stream_cm)
    client_cm = AsyncMock()
    client_cm.__aenter__.return_value = http_client
    return patch("httpx.AsyncClient", return_value=client_cm)


def _probe(client, url="https://example.com/mcp", typ="http"):
    return client.post("/api/mcp/registry/probe",
                       json={"url": url, "type": typ}).json()


def test_probe_needs_oauth_on_401_with_challenge(client):
    with _mock_stream(401, www='Bearer resource_metadata="https://x"'):
        d = _probe(client)
    assert d["status"] == "needs_oauth"


def test_probe_needs_credentials_on_bare_403(client):
    with _mock_stream(403):
        d = _probe(client)
    assert d["status"] == "needs_credentials"


def test_probe_open_on_success(client):
    with _mock_stream(200):
        d = _probe(client)
    assert d["status"] == "open"


def test_probe_unreachable_on_network_error(client):
    import httpx
    with _mock_stream(0, exc=httpx.ConnectError("boom")):
        d = _probe(client)
    assert d["status"] == "unreachable"


def test_probe_rejects_non_http_url(client):
    r = client.post("/api/mcp/registry/probe",
                    json={"url": "file:///etc/passwd"})
    assert r.status_code == 400
