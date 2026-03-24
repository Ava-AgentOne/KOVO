"""
FastAPI routes: /health and Telegram webhook endpoint.
"""
import logging

from fastapi import APIRouter, Request
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
    """Receive Telegram updates via webhook and dispatch to the bot."""
    tg_app = request.app.state.tg_app
    data = await request.json()
    update = Update.de_json(data, tg_app.bot)
    await tg_app.process_update(update)
    return {"ok": True}
