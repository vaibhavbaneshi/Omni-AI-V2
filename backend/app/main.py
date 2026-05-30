from contextlib import asynccontextmanager
import logging
from pathlib import Path

import app.core.chroma_client  # noqa: F401 — silence Chroma telemetry before other imports

from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.app_settings import configure_langsmith_env, get_settings
from app.core.health import run_health_checks, run_startup_checks
from app.core.logging_config import setup_logging
from app.core.startup import log_startup_diagnostics
from app.db.migrations import run_migrations
from app.api.user_routes import router as user_router
from app.api.chat_routes import router as chat_router
from app.api.upload_routes import router as upload_router
from app.api.session_routes import router as session_router
from app.api.oauth_routes import router as oauth_router
from app.api.memory_routes import router as memory_router
from app.api.evaluation_routes import router as evaluation_router
from app.api.analytics_routes import router as analytics_router
from app.api.model_routes import router as model_router
from app.api.settings_routes import router as settings_router
from app.middleware.production import (
    InMemoryRateLimitMiddleware,
    SecurityHeadersMiddleware,
    TraceMiddleware,
)

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.validate_for_runtime()
    configure_langsmith_env(settings)
    log_startup_diagnostics(settings)
    try:
        run_migrations()
    except Exception as exc:
        logger.error("Database migration failed: %s", exc, exc_info=exc)
        logger.warning(
            "Continuing startup without migrations; auth and persistence may fail until "
            "`alembic upgrade head` succeeds."
        )
    startup = run_startup_checks()
    logger.info("Startup complete: %s", startup.get("status"))
    yield
    logger.info("Shutting down %s", settings.APP_NAME)


settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    InMemoryRateLimitMiddleware,
    requests_per_minute=settings.RATE_LIMIT_PER_MINUTE,
)
app.add_middleware(TraceMiddleware)

AVATAR_DIR = Path(__file__).resolve().parent.parent / "uploads" / "avatars"
if AVATAR_DIR.exists():
    app.mount("/uploads/avatars", StaticFiles(directory=str(AVATAR_DIR)), name="avatars")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception:
        logger.exception(
            "Unhandled exception while processing request %s %s",
            request.method,
            request.url,
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error. Check backend logs for details."},
        )


@app.get("/")
def root():
    return {"message": "OmniAI Backend Running", "environment": settings.ENVIRONMENT}


@app.get("/health")
def health(
    deep: bool = Query(default=False, description="Probe database, Chroma, and LLM network"),
):
    return run_health_checks(
        probe_llm_network=deep,
        probe_dependencies=deep,
    )


app.include_router(user_router)
app.include_router(chat_router)
app.include_router(upload_router)
app.include_router(session_router)
app.include_router(oauth_router)
app.include_router(memory_router)
app.include_router(evaluation_router)
app.include_router(analytics_router)
app.include_router(model_router)
app.include_router(settings_router)
