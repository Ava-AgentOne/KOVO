"""
Kovo Gateway — FastAPI application.

Start modes:
  Webhook: WEBHOOK_URL env var set → registers webhook with Telegram, serves /webhook
  Polling: no WEBHOOK_URL → uses long-polling (good for dev/local testing)
"""
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.gateway import config as cfg
from src.gateway.routes import router as api_router
from src.gateway.setup import router as setup_router
from src.dashboard.api import router as dashboard_api_router

# Unified log format — all loggers (app + uvicorn) use the same timestamped format
_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
_LOG_DATEFMT = "%Y-%m-%d %H:%M:%S"

logging.basicConfig(
    level=logging.INFO,
    format=_LOG_FORMAT,
    datefmt=_LOG_DATEFMT,
)
log = logging.getLogger(__name__)

# Force uvicorn loggers to use the same format and handler as the rest of the app
from src.gateway.config import TokenMaskFilter as _TokenMaskFilter  # noqa: E402
_mask = _TokenMaskFilter()
for _h in logging.root.handlers:
    _h.addFilter(_mask)

for _uvicorn_logger in ("uvicorn", "uvicorn.error", "uvicorn.access"):
    _uv_log = logging.getLogger(_uvicorn_logger)
    _uv_log.handlers.clear()
    _uv_log.propagate = True  # inherit root handler (same format + file)
    _uv_log.addFilter(_mask)

# Set log timestamps to configured timezone (must be before first log call)
import time as _time
from src.utils.tz import get_tz as _get_log_tz
try:
    _offset_secs = int(_get_log_tz().utcoffset(None).total_seconds())
    def _tz_log_converter(*args):
        return _time.gmtime(_time.time() + _offset_secs)
    logging.Formatter.converter = _tz_log_converter
except Exception:
    pass  # Fall back to system timezone if config not ready

_FRONTEND_DIST = Path(__file__).resolve().parents[2] / "src/dashboard/frontend/dist"


def _build_deps():
    """Instantiate all shared dependencies."""
    from src.agents.kovo import KovoAgent
    from src.agents.sub_agent import SubAgentRunner
    from src.memory.auto_extract import AutoMemoryExtractor
    from src.memory.manager import MemoryManager
    from src.memory.structured_store import StructuredStore
    from src.router.classifier import MessageClassifier
    from src.router.model_router import ModelRouter
    from src.skills.creator import SkillCreator
    from src.skills.registry import SkillRegistry
    from src.tools.ollama import OllamaClient
    from src.tools.registry import ToolRegistry
    import src.tools.claude_cli as claude_cli_mod

    workspace = cfg.workspace_dir()
    skills_dir = workspace / "skills"

    ollama = OllamaClient(
        base_url=cfg.ollama_url(),
        default_model=cfg.ollama_default_model(),
    )
    memory = MemoryManager(workspace_dir=workspace)
    store = StructuredStore()

    from src.tools.reminders import ReminderManager
    reminder_mgr = ReminderManager(db_path=cfg.data_dir() / "kovo.db")
    auto_extractor = AutoMemoryExtractor(memory_manager=memory, structured_store=store)
    skills = SkillRegistry(skills_dir=skills_dir)
    creator = SkillCreator(skills_dir=skills_dir, registry=skills)
    tool_registry = ToolRegistry(workspace_dir=workspace)
    classifier = MessageClassifier()
    router = ModelRouter(classifier=classifier)

    sub_agent_runner = SubAgentRunner(workspace_dir=workspace, tool_registry=tool_registry)

    agent = KovoAgent(
        memory=memory,
        router=router,
        skills=skills,
        tool_registry=tool_registry,
        sub_agent_runner=sub_agent_runner,
        structured_store=store,
    )

    # Wire structured store into claude_cli for permission audit logging
    claude_cli_mod._structured_store = store

    from src.tools.transcribe import Transcriber
    t_cfg = cfg.get().get("transcription", {})
    transcriber = Transcriber(
        groq_api_key=t_cfg.get("groq_api_key", ""),
        whisper_model=t_cfg.get("whisper_model", "base"),
    )

    return {
        "ollama": ollama,
        "memory": memory,
        "store": store,
        "auto_extractor": auto_extractor,
        "skills": skills,
        "creator": creator,
        "tool_registry": tool_registry,
        "agent": agent,
        "sub_agent_runner": sub_agent_runner,
        "transcriber": transcriber,
        "reminders": reminder_mgr,
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── startup ──────────────────────────────────────────────────────────────
    log.info("Starting Kovo gateway...")

    # Validate environment — warn if unconfigured, don't crash
    from src.gateway.config import EnvValidationError, validate_env, check_env_permissions
    _telegram_ok = True
    try:
        validate_env()
    except EnvValidationError as exc:
        log.warning("%s", exc)
        log.warning("Starting in DASHBOARD-ONLY mode — configure .env via the dashboard then restart")
        _telegram_ok = False
    check_env_permissions()

    # First-run onboarding (no-op for already-configured systems)
    from src.onboarding.flow import OnboardingFlow
    workspace = cfg.workspace_dir()
    onboarding = OnboardingFlow(workspace_dir=workspace)
    app.state.onboarding = onboarding
    if onboarding.is_active():
        log.info("Onboarding: first-run setup will begin when the owner sends a message")

    if not _telegram_ok:
        app.state.tg_app = None
        app.state.heartbeat = None
        app.state.agent = None
        app.state.tool_registry = None
        app.state.sub_agent_runner = None
        app.state.ollama = None
        log.info("Dashboard available at /dashboard — configure .env and restart to enable Telegram")
        yield
        log.info("Shutting down (dashboard-only mode)")
        return

    deps = _build_deps()

    # Storage manager — GC, disk monitoring
    from src.tools.storage import StorageManager
    storage = StorageManager()
    app.state.storage = storage
    app.state.reminders = deps.get("reminders")

    app.state.ollama = deps["ollama"]
    app.state.memory = deps["memory"]
    app.state.store = deps["store"]
    app.state.auto_extractor = deps["auto_extractor"]
    app.state.agent = deps["agent"]
    app.state.tool_registry = deps["tool_registry"]
    app.state.sub_agent_runner = deps["sub_agent_runner"]

    # Build and start Telegram app
    from src.telegram.bot import build_application
    tg_app = build_application(
        agent=deps["agent"],
        ollama=deps["ollama"],
        memory=deps["memory"],
        skills=deps["skills"],
        creator=deps["creator"],
        tool_registry=deps["tool_registry"],
        transcriber=deps["transcriber"],
        onboarding=onboarding,
        storage=storage,
        structured_store=deps["store"],
        auto_extractor=deps["auto_extractor"],
        reminders=deps.get("reminders"),
    )
    app.state.tg_app = tg_app

    # Wire TTS + caller + transcriber into the main agent
    _init_phone_tools(deps["agent"], tg_app, deps["transcriber"])

    webhook_url = os.environ.get("WEBHOOK_URL", "").strip()
    if webhook_url:
        await tg_app.initialize()
        await tg_app.bot.set_webhook(
            url=f"{webhook_url}/webhook",
            allowed_updates=["message", "callback_query"],
        )
        await tg_app.start()
        log.info("Telegram webhook registered at %s/webhook", webhook_url)
    else:
        log.info("No WEBHOOK_URL — starting long-polling mode")
        await tg_app.initialize()
        await tg_app.start()
        await tg_app.updater.start_polling(drop_pending_updates=True)
        log.info("Telegram polling started")

    # Heartbeat scheduler
    from src.heartbeat.reporter import HeartbeatReporter
    from src.heartbeat.scheduler import HeartbeatScheduler
    hb_cfg = cfg.get().get("heartbeat", {})
    reporter = HeartbeatReporter(
        tg_app=tg_app,
        owner_user_id=cfg.allowed_users()[0],
        structured_store=deps["store"],
    )
    heartbeat = HeartbeatScheduler(
        reporter=reporter,
        ollama=deps["ollama"],
        memory=deps["memory"],
        quick_interval_minutes=int(hb_cfg.get("quick_interval", 30)),
        full_interval_hours=int(hb_cfg.get("full_interval", 6)),
        morning_time=str(hb_cfg.get("morning_time", "08:00")),
        storage=storage,
        auto_extractor=deps["auto_extractor"],
    )
    heartbeat.start()
    app.state.heartbeat = heartbeat
    tg_app.bot_data["heartbeat"] = heartbeat

    # Wire bot + reminders into heartbeat scheduler
    heartbeat._tg_bot = tg_app.bot
    heartbeat._owner_user_id = cfg.allowed_users()[0]
    heartbeat._reminders = deps.get("reminders")
    heartbeat._agent = deps["agent"]

    # Attach caller to heartbeat for session health monitoring
    agent = deps["agent"]
    if agent.caller:
        heartbeat._caller = agent.caller
        heartbeat._reporter = reporter

    log.info("Kovo fully started (1 main agent, %d sub-agents, %d skills, %d tools)",
             len(deps["sub_agent_runner"].all()),
             len(deps["skills"].all()),
             len(deps["tool_registry"].all()))

    yield

    # ── shutdown ─────────────────────────────────────────────────────────────
    log.info("Shutting down Kovo...")
    heartbeat.stop()
    if tg_app.updater and tg_app.updater.running:
        await tg_app.updater.stop()
    await tg_app.stop()
    await tg_app.shutdown()
    log.info("Kovo shutdown complete")


def _init_phone_tools(agent, tg_app, transcriber=None):
    """Wire TTS + Telegram caller + transcriber into KovoAgent."""
    try:
        from src.tools.tts import TTSEngine
        from src.tools.telegram_call import TelegramCaller
        call_cfg = cfg.get().get("telegram_call", {})
        tts_cfg = call_cfg.get("tts", {})

        agent.tts = TTSEngine(
            backend=tts_cfg.get("backend", "edge-tts"),
            voice=tts_cfg.get("voice", "en-US-GuyNeural"),
        )
        agent.caller = TelegramCaller(
            api_id=int(call_cfg.get("api_id", 0)),
            api_hash=str(call_cfg.get("api_hash", "")),
            session_name=call_cfg.get("session_name", "kovo_caller"),
            call_timeout=int(call_cfg.get("call_timeout", 30)),
        )
        agent.tg_bot = tg_app.bot
        agent.owner_user_id = cfg.allowed_users()[0]
        agent.transcriber = transcriber  # enables live voice conversation on calls
        log.info("Phone tools configured (TTS=%s)", agent.tts.backend)
    except Exception as e:
        log.warning("Phone tools init failed (telegram_call may not be configured): %s", e)


app = FastAPI(title="Kovo Gateway", version="0.8", lifespan=lifespan)

# API routes
app.include_router(api_router)
app.include_router(setup_router)
app.include_router(dashboard_api_router)

# Serve built React SPA — catch-all that serves exact files or falls back to index.html.
# StaticFiles(html=True) does NOT do SPA fallback; it only serves index.html for directory
# paths and returns 404 for unmatched routes like /dashboard/chat. We handle it manually.
if _FRONTEND_DIST.exists():
    from fastapi.responses import FileResponse as _FileResponse

    @app.get("/dashboard", include_in_schema=False)
    async def dashboard_root_redirect():
        """Redirect /dashboard to /dashboard/setup if .env is unconfigured."""
        from src.gateway.config import _ENV_PATH
        env_content = _ENV_PATH.read_text() if _ENV_PATH.exists() else ""
        needs_setup = not env_content or "TELEGRAM_BOT_TOKEN=
" in env_content or "TELEGRAM_BOT_TOKEN=" not in env_content
        if needs_setup:
            from fastapi.responses import RedirectResponse
            return RedirectResponse("/dashboard/setup")
        from fastapi.responses import RedirectResponse
        return RedirectResponse("/dashboard/overview")

    @app.get("/dashboard/{full_path:path}", include_in_schema=False)
    async def serve_dashboard_spa(full_path: str):
        # Serve the exact file if it exists (assets, favicon, etc.)
        candidate = _FRONTEND_DIST / full_path
        if candidate.is_file():
            return _FileResponse(candidate)
        # SPA fallback: always serve index.html so React Router handles the path
        return _FileResponse(_FRONTEND_DIST / "index.html")

    pass  # SPA route registered — logged at startup
else:
    log.warning("Dashboard not built yet (run: cd src/dashboard/frontend && npm run build)")


def main() -> None:
    uvicorn.run(
        "src.gateway.main:app",
        host=cfg.gateway_host(),
        port=cfg.gateway_port(),
        reload=False,
        log_level="info",
        access_log=True,
    )


if __name__ == "__main__":
    main()
