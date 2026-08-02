"""
OAuth client for remote MCP servers (v3.1) — "the Store that signs in".

Modern hosted MCP servers authenticate per the MCP authorization spec:
401 + WWW-Authenticate pointing at protected-resource metadata, an OAuth
2.1 authorization server with Dynamic Client Registration, and an
authorization-code + PKCE flow in the user's browser. Kovo's dashboard IS
in the user's browser, so it can run that flow end to end:

  Store "Connect with sign-in" → /api/mcp/oauth/start (discovery + DCR +
  PKCE, returns the consent URL) → user approves at the provider →
  /api/mcp/oauth/callback exchanges the code → tokens stored here →
  external_servers() injects "Authorization: Bearer <token>" (refreshing
  when expired) every time the brain's MCP config is built.

Store file: data/mcp_oauth.json (written atomically, 0600, never returned
by any API) — {"servers": {name: tokens}, "clients": {issuer|redirect:
registration}}. Client registrations are REUSED across sign-in attempts so
retries don't mint orphaned clients at the provider (and don't trip DCR
rate limits).

All HTTP here is synchronous httpx — async callers wrap in
asyncio.to_thread.
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import secrets
import time

import httpx

from src.utils.platform import data_path

log = logging.getLogger(__name__)

_STORE_FILE = "mcp_oauth.json"
_STATE_TTL = 600           # seconds to complete a consent flow
_STATE_CAP = 50
_REFRESH_MARGIN = 60       # refresh this many seconds before expiry
_TIMEOUT = 10.0

# In-memory pending flows: {state: {...pkce/client/context, created}}
_pending: dict[str, dict] = {}


def _valid_endpoint(url) -> bool:
    """Provider metadata is untrusted input; endpoints must be absolute
    http(s) URLs (a javascript: authorization_endpoint would otherwise be
    handed to the browser to navigate to)."""
    return isinstance(url, str) and url.lower().startswith(("https://", "http://"))


# ── Token store ───────────────────────────────────────────────────────────────

def _store_path():
    return data_path() / _STORE_FILE


def _load_store() -> dict:
    try:
        p = _store_path()
        data = json.loads(p.read_text()) if p.exists() else {}
    except Exception:
        log.warning("mcp_oauth: token store unreadable — starting empty")
        data = {}
    data.setdefault("servers", {})
    data.setdefault("clients", {})
    return data


def _save_store(store: dict) -> None:
    """Atomic, private write: 0600 from the first byte, rename into place."""
    p = _store_path()
    tmp = p.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w") as f:
            f.write(json.dumps(store))
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    os.replace(tmp, p)


def has_token(server: str) -> bool:
    return server in _load_store()["servers"]


def forget(server: str) -> bool:
    store = _load_store()
    if store["servers"].pop(server, None) is None:
        return False
    _save_store(store)
    return True


# ── Discovery (RFC 9728 protected resource + RFC 8414 / OIDC metadata) ───────

def _fetch_json(client: httpx.Client, url: str) -> dict | None:
    try:
        r = client.get(url)
        if r.is_success:
            return r.json()
    except Exception:
        pass
    return None


def _origin(url: str) -> str:
    u = httpx.URL(url)
    return f"{u.scheme}://{u.host}" + (f":{u.port}" if u.port else "")


def discover(mcp_url: str) -> dict:
    """From an MCP endpoint URL to its authorization-server metadata.

    Returns {resource, issuer, authorization_endpoint, token_endpoint,
    registration_endpoint}. Raises ValueError with a readable message on
    any gap — callers surface it to the dashboard.
    """
    origin = _origin(mcp_url)
    path = httpx.URL(mcp_url).path.rstrip("/")

    with httpx.Client(timeout=_TIMEOUT, follow_redirects=True) as client:
        # Protected-resource metadata: path-aware first, then root.
        prm = None
        for candidate in (
            f"{origin}/.well-known/oauth-protected-resource{path}",
            f"{origin}/.well-known/oauth-protected-resource",
        ):
            prm = _fetch_json(client, candidate)
            if prm:
                break
        auth_servers = (prm or {}).get("authorization_servers") or []
        issuer = auth_servers[0] if auth_servers else origin
        if not _valid_endpoint(issuer):
            raise ValueError("The server's sign-in metadata is invalid.")

        # The advertised resource identifier must belong to the MCP server
        # we're connecting — otherwise a hostile server could point the
        # token request at someone else's resource.
        resource = (prm or {}).get("resource") or mcp_url
        if not _valid_endpoint(resource) or _origin(resource) != origin:
            resource = mcp_url

        iorigin = _origin(issuer)
        ipath = httpx.URL(issuer).path.rstrip("/")
        # MCP auth spec ordering: OAuth AS metadata (path-inserted, then
        # root), then OIDC discovery (path-inserted, path-appended, root).
        candidates = [
            f"{iorigin}/.well-known/oauth-authorization-server{ipath}",
            f"{iorigin}/.well-known/oauth-authorization-server",
            f"{iorigin}/.well-known/openid-configuration{ipath}",
            f"{issuer.rstrip('/')}/.well-known/openid-configuration",
            f"{iorigin}/.well-known/openid-configuration",
        ]
        meta = None
        seen = set()
        for candidate in candidates:
            if candidate in seen:
                continue
            seen.add(candidate)
            meta = _fetch_json(client, candidate)
            if meta and meta.get("authorization_endpoint"):
                break
    if not meta or not meta.get("authorization_endpoint") or not meta.get("token_endpoint"):
        raise ValueError("The server's sign-in metadata could not be discovered.")
    for key in ("authorization_endpoint", "token_endpoint"):
        if not _valid_endpoint(meta[key]):
            raise ValueError("The provider's sign-in endpoints are invalid.")
    reg = meta.get("registration_endpoint")
    return {
        "resource": resource,
        "issuer": issuer,
        "authorization_endpoint": meta["authorization_endpoint"],
        "token_endpoint": meta["token_endpoint"],
        "registration_endpoint": reg if _valid_endpoint(reg) else None,
    }


# ── Dynamic client registration (RFC 7591) — cached per issuer ───────────────

def _client_key(issuer: str, redirect_uri: str) -> str:
    return f"{issuer}|{redirect_uri}"


def _drop_cached_client(issuer: str, redirect_uri: str) -> None:
    store = _load_store()
    if store["clients"].pop(_client_key(issuer, redirect_uri), None) is not None:
        _save_store(store)


def register_client(meta: dict, redirect_uri: str) -> dict:
    """Kovo's OAuth client for this issuer — reused across attempts.

    Registering fresh on every click orphans clients at the provider and
    trips DCR rate limits, so the first successful registration is cached
    per (issuer, redirect_uri)."""
    store = _load_store()
    cached = store["clients"].get(_client_key(meta["issuer"], redirect_uri))
    if cached and cached.get("client_id"):
        return cached

    endpoint = meta.get("registration_endpoint")
    if not endpoint:
        raise ValueError("The provider does not support automatic client "
                         "registration — this server can't be connected yet.")
    payload = {
        "client_name": "KOVO",
        "redirect_uris": [redirect_uri],
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none",
    }
    with httpx.Client(timeout=_TIMEOUT) as client:
        r = client.post(endpoint, json=payload)
        if not r.is_success:
            raise ValueError(f"Client registration was rejected "
                             f"(HTTP {r.status_code}).")
        data = r.json()
    if not data.get("client_id"):
        raise ValueError("Client registration returned no client id.")
    info = {"client_id": data["client_id"],
            "client_secret": data.get("client_secret")}
    store = _load_store()
    store["clients"][_client_key(meta["issuer"], redirect_uri)] = info
    _save_store(store)
    return info


# ── PKCE + flow state ────────────────────────────────────────────────────────

def _pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(48)
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


def _prune_pending() -> None:
    now = time.time()
    for s in [s for s, v in _pending.items()
              if now - v["created"] > _STATE_TTL]:
        del _pending[s]
    while len(_pending) > _STATE_CAP:
        del _pending[min(_pending, key=lambda s: _pending[s]["created"])]


def start_connect(server: str, mcp_url: str, redirect_uri: str) -> str:
    """Discovery + registration + PKCE. Returns the browser consent URL."""
    import urllib.parse
    meta = discover(mcp_url)
    client_info = register_client(meta, redirect_uri)

    _prune_pending()
    verifier, challenge = _pkce_pair()
    state = secrets.token_urlsafe(24)
    _pending[state] = {
        "server": server,
        "mcp_url": mcp_url,
        "verifier": verifier,
        "redirect_uri": redirect_uri,
        "issuer": meta["issuer"],
        "token_endpoint": meta["token_endpoint"],
        "client_id": client_info["client_id"],
        "client_secret": client_info.get("client_secret"),
        "resource": meta["resource"],
        "created": time.time(),
    }
    params = {
        "response_type": "code",
        "client_id": client_info["client_id"],
        "redirect_uri": redirect_uri,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        # RFC 8707 resource indicator — the MCP spec requires it so the
        # token is bound to this specific server.
        "resource": meta["resource"],
    }
    return meta["authorization_endpoint"] + "?" + urllib.parse.urlencode(params)


def complete_connect(state: str, code: str) -> str:
    """Exchange the callback code for tokens. Returns the server name."""
    ctx = _pending.pop(state, None)
    if not ctx or (time.time() - ctx["created"]) > _STATE_TTL:
        raise ValueError("This sign-in link expired — please try again.")
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": ctx["redirect_uri"],
        "client_id": ctx["client_id"],
        "code_verifier": ctx["verifier"],
        "resource": ctx["resource"],
    }
    if ctx.get("client_secret"):
        data["client_secret"] = ctx["client_secret"]
    with httpx.Client(timeout=_TIMEOUT) as client:
        r = client.post(ctx["token_endpoint"], data=data)
        if not r.is_success:
            log.error("mcp_oauth: token exchange failed for %s: %s",
                      ctx["server"], r.text[:300])
            # A cached registration the provider no longer recognizes
            # would fail every retry — drop it so the next attempt
            # re-registers cleanly.
            if "invalid_client" in r.text[:300]:
                _drop_cached_client(ctx["issuer"], ctx["redirect_uri"])
            raise ValueError("The provider rejected the sign-in — please try again.")
        tok = r.json()
    if not tok.get("access_token"):
        raise ValueError("The provider returned no access token.")
    expires_in = tok.get("expires_in")
    store = _load_store()
    store["servers"][ctx["server"]] = {
        "access_token": tok["access_token"],
        "refresh_token": tok.get("refresh_token"),
        # None = the provider declared no expiry — treat as non-expiring
        "expires_at": time.time() + int(expires_in) if expires_in else None,
        "mcp_url": ctx["mcp_url"],
        "issuer": ctx["issuer"],
        "token_endpoint": ctx["token_endpoint"],
        "client_id": ctx["client_id"],
        "client_secret": ctx.get("client_secret"),
        "resource": ctx["resource"],
    }
    _save_store(store)
    log.info("mcp_oauth: connected %r", ctx["server"])
    return ctx["server"]


# ── Access (with lazy refresh) — called when brain MCP config is built ───────

def get_access_token(server: str, mcp_url: str | None = None) -> str | None:
    """The Bearer token for a connected server, refreshed when stale.

    When *mcp_url* is given it must match the URL the token was minted
    for — a renamed/repointed server entry never receives another
    server's token."""
    store = _load_store()
    tok = store["servers"].get(server)
    if not tok:
        return None
    if mcp_url and tok.get("mcp_url") and tok["mcp_url"] != mcp_url:
        log.warning("mcp_oauth: %r URL changed since sign-in — token "
                    "withheld; sign in again from the dashboard", server)
        return None
    expires_at = tok.get("expires_at")
    if expires_at is None or time.time() < expires_at - _REFRESH_MARGIN:
        return tok["access_token"]
    if not tok.get("refresh_token"):
        log.warning("mcp_oauth: %r token expired and no refresh token — "
                    "sign in again from the dashboard", server)
        return None
    data = {
        "grant_type": "refresh_token",
        "refresh_token": tok["refresh_token"],
        "client_id": tok["client_id"],
        "resource": tok.get("resource", ""),
    }
    if tok.get("client_secret"):
        data["client_secret"] = tok["client_secret"]
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            r = client.post(tok["token_endpoint"], data=data)
            if not r.is_success:
                log.warning("mcp_oauth: refresh failed for %r (HTTP %s) — "
                            "sign in again from the dashboard",
                            server, r.status_code)
                return None
            new = r.json()
    except Exception as e:
        log.warning("mcp_oauth: refresh error for %r: %s", server, e)
        # Network hiccup — the old token MAY still be valid; let the
        # server be the judge rather than silently dropping it.
        return tok["access_token"]
    if not new.get("access_token"):
        return None
    tok["access_token"] = new["access_token"]
    if new.get("refresh_token"):                 # rotation
        tok["refresh_token"] = new["refresh_token"]
    expires_in = new.get("expires_in")
    tok["expires_at"] = time.time() + int(expires_in) if expires_in else None
    store["servers"][server] = tok
    _save_store(store)
    return tok["access_token"]
