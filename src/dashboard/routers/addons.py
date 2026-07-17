"""
Add-ons endpoints (v3.0 Phase 3.5) — guided companion setup.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from src.dashboard.auth import require_auth
from src.tools import addons

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api", dependencies=[Depends(require_auth)])


@router.get("/addons")
async def list_addons():
    return {"addons": addons.list_with_status()}


@router.get("/addons/job")
async def install_job_status():
    return addons.job_status()


@router.get("/addons/{addon_id}/commands")
async def addon_commands(addon_id: str):
    """The exact commands an install would run — shown before confirming."""
    entry = addons.get(addon_id)
    if not entry:
        raise HTTPException(404, "Unknown add-on")
    return {"commands": entry.get("install_commands") or []}


@router.post("/addons/{addon_id}/install")
async def install_addon(addon_id: str):
    try:
        return addons.start_install(addon_id)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/addons/tailscale/login")
async def tailscale_login():
    result = await addons.tailscale_login_url()
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.post("/addons/google/credentials")
async def google_credentials(file: UploadFile = File(...)):
    """Upload the OAuth client credentials.json from Google Cloud Console."""
    import json
    from src.utils.platform import config_path
    raw = await file.read()
    if len(raw) > 100_000:
        raise HTTPException(400, "File too large for a credentials.json")
    try:
        parsed = json.loads(raw)
        if "installed" not in parsed and "web" not in parsed:
            raise ValueError
    except Exception:
        raise HTTPException(400, "Not a valid Google OAuth credentials.json")
    dest = config_path() / "google-credentials.json"
    dest.write_bytes(raw)
    dest.chmod(0o600)
    return {"saved": True}


@router.post("/addons/google/auth/start")
async def google_auth_start():
    try:
        return addons.google_auth_start()
    except Exception as e:
        raise HTTPException(400, str(e)[:200])


class AuthCompleteBody(BaseModel):
    code_or_url: str


@router.post("/addons/google/auth/complete")
async def google_auth_complete(body: AuthCompleteBody):
    try:
        return addons.google_auth_complete(body.code_or_url)
    except ValueError as e:
        raise HTTPException(400, str(e))


class PullBody(BaseModel):
    model: str = "llama3.2:3b"


@router.post("/addons/ollama/pull")
async def ollama_pull(body: PullBody):
    try:
        return addons.ollama_pull(body.model)
    except ValueError as e:
        raise HTTPException(400, str(e))
