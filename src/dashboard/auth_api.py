"""
Auth endpoints — the only /api routes that work without a session.

POST /api/auth/request             start a Telegram-approved login
GET  /api/auth/status/<id>         poll; sets the session cookie once approved
POST /api/auth/logout              revoke the current session
GET  /api/auth/me                  200 if authenticated (or unconfigured), else 401

GET  /api/auth/google/login        redirect to Google OAuth consent screen
GET  /api/auth/google/callback     handle Google OAuth callback → permanent session
"""
from __future__ import annotations

import logging
import os
import secrets as _secrets
import time
import urllib.parse

import httpx
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import RedirectResponse

from src.dashboard import auth

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth")

# ── Google OAuth helpers ──────────────────────────────────────────────────────

_GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
_GOOGLE_SESSION_TTL = 365 * 24 * 3600          # 1 year — "permanent"
_GOOGLE_STATE_TTL = 600                         # 10 min to complete the flow

# In-memory state store for CSRF protection: {state: {redirect_uri, created}}
_google_states: dict[str, dict] = {}


def _google_redirect_uri(request: Request) -> str:
    """Build the redirect URI from the incoming request's base URL."""
    base = str(request.base_url).rstrip("/")
    return f"{base}/api/auth/google/callback"


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post("/request")
async def auth_request(request: Request):
    if not auth.is_configured():
        raise HTTPException(409, "Setup not complete — no login needed yet")
    tg_app = getattr(request.app.state, "tg_app", None)
    if tg_app is None:
        raise HTTPException(503, "Telegram bot not running — cannot deliver approval")

    from src.gateway import config as cfg
    owner_id = cfg.allowed_users()[0]

    req = auth.create_login_request(_client_ip(request))

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Approve", callback_data=f"auth_approve:{req['request_id']}"),
        InlineKeyboardButton("❌ Deny", callback_data=f"auth_deny:{req['request_id']}"),
    ]])
    await tg_app.bot.send_message(
        chat_id=owner_id,
        text=(
            "🔐 *Dashboard login request*\n\n"
            f"Code: `{req['code']}`\n"
            f"From: `{_client_ip(request)}`\n\n"
            "Approve only if this code matches your screen."
        ),
        parse_mode="Markdown",
        reply_markup=keyboard,
    )
    return {"request_id": req["request_id"], "code": req["code"], "expires_in": req["expires_in"]}


@router.get("/status/{request_id}")
async def auth_status(request_id: str, request: Request, response: Response):
    req = auth.get_request(request_id)
    if req is None:
        return {"status": "expired"}
    if req["status"] == "approved":
        auth.consume_approved(request_id)
        cookie = auth.create_session(_client_ip(request))
        response.set_cookie(
            auth.COOKIE_NAME, cookie,
            max_age=auth.SESSION_TTL, httponly=True, samesite="lax", path="/",
        )
        return {"status": "approved"}
    return {"status": req["status"]}


@router.post("/logout")
async def auth_logout(request: Request, response: Response):
    sid = auth.validate_cookie(request.cookies.get(auth.COOKIE_NAME))
    if sid:
        auth.revoke_session(sid)
    response.delete_cookie(auth.COOKIE_NAME, path="/")
    return {"logged_out": True}


@router.get("/me")
async def auth_me(request: Request):
    if not auth.is_configured():
        return {"authenticated": True, "setup_mode": True}
    if auth.validate_cookie(request.cookies.get(auth.COOKIE_NAME)):
        return {"authenticated": True}
    raise HTTPException(401, "Not authenticated")


# ── Google OAuth ──────────────────────────────────────────────────────────────

# These endpoints are full-page browser navigations (not fetch calls), so
# user-facing failures redirect back to the SPA login page — Login.jsx maps
# the ?error= codes to friendly messages — instead of dumping raw JSON.
# NOTE: the SPA is served under /dashboard/*, so redirects must target
# /dashboard/... ("/" and "/login" are 404s on this gateway).

_LOGIN_PAGE = "/dashboard/login"
_HOME_PAGE = "/dashboard/"


def _login_error(code: str) -> RedirectResponse:
    return RedirectResponse(f"{_LOGIN_PAGE}?error={code}", status_code=302)


def _google_env() -> tuple[str, str, str]:
    return (os.environ.get("GOOGLE_CLIENT_ID", "").strip(),
            os.environ.get("GOOGLE_CLIENT_SECRET", "").strip(),
            os.environ.get("GOOGLE_ALLOWED_EMAIL", "").strip().lower())


def _google_configured() -> bool:
    return all(_google_env())


def _google_redirect_uri(request: Request) -> str:
    """The OAuth callback URL.

    GOOGLE_REDIRECT_URI wins when set — Google only accepts https redirect
    URIs (http://localhost excepted), so remote setups register an https
    URL (e.g. via `tailscale serve`) and pin it here. The fallback derives
    from the request, which also keeps the value out of Host-header control
    whenever the override is set.
    """
    override = os.environ.get("GOOGLE_REDIRECT_URI", "").strip()
    if override:
        return override
    base = str(request.base_url).rstrip("/")
    return f"{base}/api/auth/google/callback"


def _prune_google_states() -> None:
    now = time.time()
    for s in [s for s, v in _google_states.items()
              if now - v["created"] > _GOOGLE_STATE_TTL]:
        del _google_states[s]
    # Hard cap so an unauthenticated caller can't grow memory inside the TTL
    # window: drop oldest first.
    while len(_google_states) > 100:
        oldest = min(_google_states, key=lambda s: _google_states[s]["created"])
        del _google_states[oldest]


@router.get("/methods")
async def auth_methods():
    """Which login methods this server offers (Login.jsx hides the rest)."""
    return {"telegram": True, "google": _google_configured()}


@router.get("/google/login")
async def google_login(request: Request):
    """Redirect the browser to Google's OAuth consent screen."""
    client_id, _, _ = _google_env()
    if not _google_configured():
        log.warning("Google login attempted but not configured "
                    "(need GOOGLE_CLIENT_ID + GOOGLE_CLIENT_SECRET + "
                    "GOOGLE_ALLOWED_EMAIL in config/.env)")
        return _login_error("google_unconfigured")

    _prune_google_states()
    redirect_uri = _google_redirect_uri(request)
    state = _secrets.token_urlsafe(24)
    _google_states[state] = {"redirect_uri": redirect_uri, "created": time.time()}

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email",
        "state": state,
        "prompt": "select_account",
    }
    return RedirectResponse(_GOOGLE_AUTH_URL + "?" + urllib.parse.urlencode(params))


@router.get("/google/callback")
async def google_callback(request: Request, state: str = "", code: str = "",
                          error: str = ""):
    """Exchange the Google auth code for a long-lived KOVO session."""
    if error:
        # `error` is attacker-typeable on this pre-auth endpoint — never log
        # the raw value (CRLF in it would forge log lines).
        log.warning("Google OAuth returned an error (user denied or provider error)")
        return _login_error("google_denied")

    # Validate CSRF state (single-use: popped even on later failures)
    state_data = _google_states.pop(state, None)
    if not state_data or (time.time() - state_data["created"]) > _GOOGLE_STATE_TTL:
        return _login_error("google_state")

    client_id, client_secret, allowed_email = _google_env()
    if not _google_configured():
        return _login_error("google_unconfigured")

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            token_resp = await client.post(_GOOGLE_TOKEN_URL, data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": state_data["redirect_uri"],
                "grant_type": "authorization_code",
            })
            if not token_resp.is_success:
                log.error("Google token exchange failed: %s",
                          token_resp.text[:300])
                return _login_error("google_error")

            access_token = token_resp.json().get("access_token", "")

            user_resp = await client.get(
                _GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if not user_resp.is_success:
                log.error("Google userinfo failed: %s", user_resp.text[:300])
                return _login_error("google_error")
    except httpx.HTTPError as e:
        log.error("Google OAuth network error: %s", e)
        return _login_error("google_error")

    profile = user_resp.json()
    email = (profile.get("email") or "").strip().lower()
    log.info("Google OAuth: %s attempting dashboard login", email)

    # Require a positively verified email: Google issues accounts whose
    # profile email is an arbitrary unverified address on someone else's
    # domain — matching the allowlist alone is not proof of ownership.
    if not email or profile.get("verified_email") is not True:
        log.warning("Google OAuth: rejected profile without verified email")
        return _login_error("google_forbidden")
    if email != allowed_email:
        log.warning("Google OAuth: rejected email %s (not the allowed owner)",
                    email)
        return _login_error("google_forbidden")

    # All good — create a 1-year session (feels permanent)
    cookie = auth.create_session(_client_ip(request), ttl=_GOOGLE_SESSION_TTL)
    resp = RedirectResponse(_HOME_PAGE, status_code=302)
    resp.set_cookie(
        auth.COOKIE_NAME, cookie,
        max_age=_GOOGLE_SESSION_TTL,
        httponly=True,
        samesite="lax",
        path="/",
    )
    log.info("Google OAuth: session created for %s (1-year TTL)", email)
    return resp
