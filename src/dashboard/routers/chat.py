"""
Dashboard chat — history + WebSocket.
Split from the original src/dashboard/api.py (v2.0).
"""
from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.dashboard.auth import require_auth
from src.dashboard.routers.common import _KOVO_VERSION, _app_state, _get_memory
from src.utils.platform import kovo_dir, service_restart_cmd, service_status as _platform_service_status, get_ram_info, get_disk_info
from src.utils.tz import today as _tz_today, now as _tz_now

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api", dependencies=[Depends(require_auth)])

# In-memory chat history for the dashboard chat (dashboard user_id = 0)
_chat_history: List[dict] = []
_MAX_HISTORY = 200


# ── WebSocket Chat ─────────────────────────────────────────────────────────────

@router.get("/chat/history")
async def get_chat_history():
    """Return the in-memory dashboard chat history."""
    return {"messages": _chat_history}


@router.post("/chat/clear")
async def clear_chat_history():
    """Clear the in-memory dashboard chat history."""
    _chat_history.clear()
    return {"cleared": True}


@router.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for the dashboard chat interface.
    Connects to Kovo (user_id=0 for dashboard).
    """
    await websocket.accept()

    # Everything after accept() is wrapped so any startup error is logged
    # rather than causing a silent immediate disconnect.
    try:
        # Resolve agent from app state — scope["app"] is the FastAPI instance.
        state = websocket.scope["app"].state
        agent = getattr(state, "agent", None)

        # Send existing history on connect
        await websocket.send_json({"type": "history", "messages": _chat_history})

        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
            except json.JSONDecodeError:
                payload = {"message": data}

            message = (payload.get("message") or "").strip()
            if not message:
                continue

            # Add user message to history
            user_msg = {"role": "user", "content": message}
            _chat_history.append(user_msg)
            if len(_chat_history) > _MAX_HISTORY:
                _chat_history.pop(0)

            # Echo user message back to confirm receipt
            await websocket.send_json({"type": "message", **user_msg})

            # Signal typing
            await websocket.send_json({"type": "typing"})

            if agent is None:
                response_text = "Agent not available — system still starting up."
                model_used = "none"
            else:
                # Stream the reply as it generates (Phase 3b): throttled
                # "delta" frames carry the accumulated text so far; the
                # final "message" frame stays authoritative.
                import time as _time
                _last_delta = 0.0

                async def _ws_delta(text: str):
                    nonlocal _last_delta
                    now = _time.monotonic()
                    if now - _last_delta < 0.4:
                        return
                    _last_delta = now
                    try:
                        await websocket.send_json({"type": "delta", "content": text})
                    except Exception:
                        pass  # client gone — the final send will surface it

                try:
                    result = await agent.handle(message=message, user_id=0, on_delta=_ws_delta)
                    response_text = result.get("text", "(no response)")
                    model_used = result.get("model_used", "?")
                except Exception as e:
                    log.error("Chat agent error: %s", e)
                    response_text = f"Error: {e}"
                    model_used = "error"

            # Add assistant reply to history
            assistant_msg = {
                "role": "assistant",
                "content": response_text,
                "model": model_used,
            }
            _chat_history.append(assistant_msg)
            if len(_chat_history) > _MAX_HISTORY:
                _chat_history.pop(0)

            await websocket.send_json({"type": "message", **assistant_msg})

    except WebSocketDisconnect:
        log.info("Dashboard chat disconnected")
    except Exception as e:
        log.error("Chat WebSocket error: %s", e)
        try:
            await websocket.close()
        except Exception:
            pass
