"""
Dashboard authentication — Telegram-approved login sessions.

Flow:
  1. Browser POSTs /api/auth/request → gets a request_id + short code; KOVO
     messages the owner on Telegram with the code and Approve/Deny buttons.
  2. Owner taps Approve (code on screen must match the code in the message).
  3. Browser polls /api/auth/status/<request_id> → on approval receives a
     signed session cookie (HttpOnly, 30 days).

Sessions persist in data/dashboard_sessions.json so a service restart does
not log the owner out. The signing secret lives in data/dashboard_secret.key
(created on first use, mode 600). While the install is UNCONFIGURED (no
TELEGRAM_BOT_TOKEN in .env) auth is bypassed entirely — the setup wizard and
backup restore must work before there is a bot to approve with.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets
import time

from fastapi import HTTPException, Request, WebSocket, WebSocketException

from src.utils.platform import data_path

log = logging.getLogger(__name__)

COOKIE_NAME = "kovo_session"
SESSION_TTL = 30 * 24 * 3600          # 30 days
REQUEST_TTL = 300                     # login request expires after 5 min
MAX_PENDING_REQUESTS = 3              # across all IPs
PER_IP_COOLDOWN = 10                  # seconds between requests from one IP

_SECRET_FILE = "dashboard_secret.key"
_SESSIONS_FILE = "dashboard_sessions.json"

_secret_cache: bytes | None = None
_sessions_cache: dict | None = None

# In-memory login requests: {request_id: {code, ip, created, status}}
# status: pending | approved | denied
_requests: dict[str, dict] = {}
_last_request_by_ip: dict[str, float] = {}


# ── secret & signing ─────────────────────────────────────────────────────────

def _secret() -> bytes:
    global _secret_cache
    if _secret_cache is None:
        path = data_path() / _SECRET_FILE
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(secrets.token_bytes(32))
            path.chmod(0o600)
            log.info("Generated new dashboard session secret")
        _secret_cache = path.read_bytes()
    return _secret_cache


def _sign(payload: str) -> str:
    return hmac.new(_secret(), payload.encode(), hashlib.sha256).hexdigest()


# ── session store ────────────────────────────────────────────────────────────

def _sessions() -> dict:
    global _sessions_cache
    if _sessions_cache is None:
        path = data_path() / _SESSIONS_FILE
        try:
            _sessions_cache = json.loads(path.read_text()) if path.exists() else {}
        except Exception:
            _sessions_cache = {}
    return _sessions_cache


def _save_sessions() -> None:
    path = data_path() / _SESSIONS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_sessions()))
    path.chmod(0o600)


def create_session(ip: str, ttl: int = SESSION_TTL) -> str:
    """Create a session and return the signed cookie value.

    Pass a custom *ttl* (seconds) to override the default 30-day expiry —
    e.g. Google-authenticated sessions use 365 days so they feel permanent.
    """
    now = int(time.time())
    # Prune expired sessions while we're here
    store = _sessions()
    for sid in [s for s, v in store.items() if v.get("expires", 0) < now]:
        del store[sid]
    sid = secrets.token_hex(16)
    store[sid] = {"created": now, "expires": now + ttl, "ip": ip}
    _save_sessions()
    payload = f"{sid}.{now + ttl}"
    return f"{payload}.{_sign(payload)}"


def validate_cookie(value: str | None) -> str | None:
    """Return the session id if the cookie is valid and unexpired, else None."""
    if not value:
        return None
    parts = value.rsplit(".", 1)
    if len(parts) != 2:
        return None
    payload, sig = parts
    if not hmac.compare_digest(_sign(payload), sig):
        return None
    try:
        sid, expires = payload.split(".")
        if int(expires) < time.time():
            return None
    except ValueError:
        return None
    session = _sessions().get(sid)
    if not session or session.get("expires", 0) < time.time():
        return None
    return sid


def revoke_session(sid: str) -> None:
    if _sessions().pop(sid, None) is not None:
        _save_sessions()


# ── login requests ───────────────────────────────────────────────────────────

def _purge_requests() -> None:
    cutoff = time.time() - REQUEST_TTL
    for rid in [r for r, v in _requests.items() if v["created"] < cutoff]:
        del _requests[rid]


def create_login_request(ip: str) -> dict:
    """Create a pending login request. Raises HTTPException on rate limit."""
    _purge_requests()
    if time.time() - _last_request_by_ip.get(ip, 0) < PER_IP_COOLDOWN:
        raise HTTPException(429, "Too many login requests — wait a few seconds")
    pending = sum(1 for v in _requests.values() if v["status"] == "pending")
    if pending >= MAX_PENDING_REQUESTS:
        raise HTTPException(429, "Too many pending login requests")
    _last_request_by_ip[ip] = time.time()
    rid = secrets.token_hex(16)
    code = f"{secrets.randbelow(1000):03d}-{secrets.randbelow(1000):03d}"
    _requests[rid] = {"code": code, "ip": ip, "created": time.time(), "status": "pending"}
    log.info("Dashboard login request from %s (code %s)", ip, code)
    return {"request_id": rid, "code": code, "expires_in": REQUEST_TTL}


def get_request(rid: str) -> dict | None:
    _purge_requests()
    return _requests.get(rid)


def resolve_request(rid: str, approved: bool) -> bool:
    """Called from the Telegram callback. Returns False if unknown/expired."""
    _purge_requests()
    req = _requests.get(rid)
    if not req or req["status"] != "pending":
        return False
    req["status"] = "approved" if approved else "denied"
    log.info("Dashboard login %s for %s", req["status"], req["ip"])
    return True


def consume_approved(rid: str) -> dict | None:
    """Pop an approved request (one-shot) and return it, else None."""
    req = _requests.get(rid)
    if req and req["status"] == "approved":
        del _requests[rid]
        return req
    return None


# ── configured check ─────────────────────────────────────────────────────────

def is_configured() -> bool:
    """True once a TELEGRAM_BOT_TOKEN exists in .env (same check as gateway)."""
    try:
        from src.gateway.config import _ENV_FILE
        env_text = _ENV_FILE.read_text() if _ENV_FILE.exists() else ""
        for line in env_text.splitlines():
            if line.startswith("TELEGRAM_BOT_TOKEN=") and line.split("=", 1)[1].strip():
                return True
    except Exception:
        pass
    return False


# ── FastAPI dependency ───────────────────────────────────────────────────────

async def require_auth(request: Request = None, websocket: WebSocket = None) -> None:
    """Guard for dashboard endpoints (HTTP and WebSocket).

    Bypassed while the install is unconfigured (setup-wizard mode).
    """
    if not is_configured():
        return
    conn = request or websocket
    cookie = conn.cookies.get(COOKIE_NAME) if conn else None
    if validate_cookie(cookie):
        return
    if websocket is not None:
        raise WebSocketException(code=1008)
    raise HTTPException(401, "Not authenticated")
