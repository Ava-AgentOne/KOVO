"""
Auth endpoints — the only /api routes that work without a session.

POST /api/auth/request        start a login (sends Telegram approval message)
GET  /api/auth/status/<id>    poll; sets the session cookie once approved
POST /api/auth/logout         revoke the current session
GET  /api/auth/me             200 if authenticated (or unconfigured), else 401
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request, Response

from src.dashboard import auth

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth")


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
