"""Tests for the Telegram webhook endpoint (/webhook) and its secret token."""
import asyncio
import re
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.channels.base import ChannelRegistry
from src.channels.telegram import TelegramChannel
from src.gateway import routes

HEADER = "X-Telegram-Bot-Api-Secret-Token"
OWNER_ID = 123456789

# A text message "from" the owner, shaped exactly like a real Telegram update.
# Everything in it, the sender included, is chosen by whoever sends the request.
UPDATE = {
    "update_id": 1,
    "message": {
        "message_id": 1,
        "date": 1700000000,
        "chat": {"id": OWNER_ID, "type": "private"},
        "from": {"id": OWNER_ID, "is_bot": False, "first_name": "Owner"},
        "text": "run a shell command",
    },
}


def _channel():
    """A TelegramChannel with a mocked bot application (no network)."""
    ch = TelegramChannel.__new__(TelegramChannel)  # skip building the real bot
    ch.app = MagicMock()
    ch.app.bot.defaults = None  # Update.de_json reads bot.defaults
    ch.app.initialize = AsyncMock()
    ch.app.start = AsyncMock()
    ch.app.bot.set_webhook = AsyncMock()
    ch.app.updater.start_polling = AsyncMock()
    ch.app.process_update = AsyncMock()
    return ch


def _client(channel=None):
    """The /webhook router wired the way the gateway wires it at startup."""
    app = FastAPI()
    app.include_router(routes.router)
    if channel is not None:
        registry = ChannelRegistry()
        registry.register(channel)
        app.state.channels = registry
        app.state.tg_app = channel.app
    return TestClient(app)


@pytest.fixture()
def webhook_channel(monkeypatch):
    monkeypatch.setenv("WEBHOOK_URL", "https://kovo.example.com")
    ch = _channel()
    asyncio.run(ch.start())
    return ch


@pytest.fixture()
def polling_channel(monkeypatch):
    monkeypatch.delenv("WEBHOOK_URL", raising=False)
    ch = _channel()
    asyncio.run(ch.start())
    return ch


# ── webhook registration ──────────────────────────────────────────────────────

def test_webhook_mode_registers_a_secret_token(webhook_channel):
    kwargs = webhook_channel.app.bot.set_webhook.await_args.kwargs
    assert kwargs["url"] == "https://kovo.example.com/webhook"
    assert kwargs["secret_token"] == webhook_channel.webhook_secret
    # Telegram accepts 1-256 characters from A-Z, a-z, 0-9, _ and -
    assert re.fullmatch(r"[A-Za-z0-9_-]{32,256}", webhook_channel.webhook_secret)


def test_polling_mode_registers_no_secret(polling_channel):
    assert polling_channel.webhook_secret is None
    polling_channel.app.bot.set_webhook.assert_not_awaited()
    polling_channel.app.updater.start_polling.assert_awaited_once()


# ── /webhook ──────────────────────────────────────────────────────────────────

def test_update_with_the_secret_is_processed(webhook_channel):
    r = _client(webhook_channel).post(
        "/webhook", json=UPDATE, headers={HEADER: webhook_channel.webhook_secret})
    assert r.status_code == 200
    update = webhook_channel.app.process_update.await_args.args[0]
    assert update.message.from_user.id == OWNER_ID
    assert update.message.text == "run a shell command"


@pytest.mark.parametrize("headers", [{}, {HEADER: ""}, {HEADER: "wrong-secret"}],
                         ids=["no-header", "empty", "wrong"])
def test_forged_update_is_rejected(webhook_channel, headers):
    r = _client(webhook_channel).post("/webhook", json=UPDATE, headers=headers)
    assert r.status_code == 403
    webhook_channel.app.process_update.assert_not_awaited()


def test_endpoint_is_off_in_polling_mode(polling_channel):
    r = _client(polling_channel).post("/webhook", json=UPDATE)
    assert r.status_code == 404
    polling_channel.app.process_update.assert_not_awaited()


def test_endpoint_is_off_without_telegram():
    # Dashboard-only mode (no bot token yet): nothing is registered
    r = _client().post("/webhook", json=UPDATE, headers={HEADER: "anything"})
    assert r.status_code == 404
