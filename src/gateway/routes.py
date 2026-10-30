"""
FastAPI routes: /health and Telegram webhook endpoint.
"""
import hmac
import logging

from fastapi import APIRouter, HTTPException, Request
from telegram import Update

log = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
async def health(request: Request) -> dict:
    app_state = request.app.state
    ollama_ok = False
    if hasattr(app_state, "ollama"):
        try:
            ollama_ok = await app_state.ollama.is_available()
        except Exception:
            pass
    return {
        "status": "ok",
        "ollama": ollama_ok,
        "telegram": "webhook",
    }


@router.post("/webhook")
async def telegram_webhook(request: Request) -> dict:
    """Receive Telegram updates via webhook and dispatch to the bot.

    The update body, sender included, is whatever the caller sends, so only
    requests carrying the secret registered with Telegram are processed. In
    polling mode, or before Telegram is configured, there is no secret and
    the endpoint does not exist.
    """
    channels = getattr(request.app.state, "channels", None)
    telegram = channels.get("telegram") if channels else None
    secret = getattr(telegram, "webhook_secret", None)
    if not secret:
        raise HTTPException(404)
    supplied = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if not hmac.compare_digest(supplied.encode(), secret.encode()):
        log.warning("Rejected /webhook request without Telegram's secret token (from %s)",
                    request.client.host if request.client else "unknown")
        raise HTTPException(403)

    tg_app = telegram.app
    data = await request.json()
    update = Update.de_json(data, tg_app.bot)
    await tg_app.process_update(update)
    return {"ok": True}
