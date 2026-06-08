from contextlib import asynccontextmanager
import logging
from pathlib import Path

import os

# Silence Chroma telemetry before chromadb is imported (lazy, on first vector-store use).
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
os.environ.setdefault("CHROMA_TELEMETRY", "FALSE")

from app.core.sentry_config import init_sentry

init_sentry()

from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.app_settings import configure_langsmith_env, get_settings
from app.core.cors_utils import cors_headers_for_request
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
from app.api.queue_routes import router as queue_router
from app.api.insights_routes import router as insights_router
from app.api import agent_routes
from app.api.folder_routes import router as folder_router
from app.api.search_routes import router as search_router
from app.middleware.production import (
    InMemoryRateLimitMiddleware,
    RedisRateLimitMiddleware,
    SecurityHeadersMiddleware,
    TraceMiddleware,
)

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    import threading

    app.state.ready = False
    app.state.startup_error = None

    def _startup() -> None:
        try:
            settings = get_settings()
            settings.validate_for_runtime()
            configure_langsmith_env(settings)
            log_startup_diagnostics(settings)

            def _migrate() -> None:
                try:
                    run_migrations()
                except Exception as exc:
                    logger.error("Database migration failed: %s", exc, exc_info=exc)

            threading.Thread(target=_migrate, name="db-migrate", daemon=True).start()

            startup = run_startup_checks()
            logger.info("Startup complete: %s", startup.get("status"))
            if settings.INGEST_IN_BACKGROUND:
                if settings.ingest_uses_rq_queue:
                    from app.services.ingestion_queue import get_active_worker_count

                    worker_count = get_active_worker_count()
                    logger.info(
                        "Document indexing: RQ queue (INGEST_QUEUE_ENABLED=true, redis=%s, workers=%s)",
                        settings.redis_url.split("@")[-1] if settings.redis_url else "unset",
                        worker_count,
                    )
                    if worker_count == 0:
                        logger.error(
                            "No RQ ingestion workers connected — uploads will stay queued. "
                            "Ensure scripts/railway_web_and_worker.sh runs in this container."
                        )
                else:
                    logger.info(
                        "Document indexing: in-process BackgroundTasks (INGEST_QUEUE_ENABLED=false)."
                    )
            else:
                logger.info("Document indexing: synchronous (INGEST_IN_BACKGROUND=false)")
            if settings.EMBEDDING_PROVIDER == "local":
                logger.warning(
                    "EMBEDDING_PROVIDER=local loads PyTorch in-process — use huggingface on Railway."
                )
            if settings.PRELOAD_EMBEDDING_MODEL and settings.EMBEDDING_PROVIDER == "local":
                threading.Thread(
                    target=lambda: __import__(
                        "app.services.embedding_service",
                        fromlist=["preload_embedding_model"],
                    ).preload_embedding_model(),
                    name="embedding-preload",
                    daemon=True,
                ).start()
            app.state.ready = True
        except Exception as exc:
            app.state.startup_error = str(exc)
            logger.critical("Startup failed: %s", exc, exc_info=exc)

    threading.Thread(target=_startup, name="app-startup", daemon=True).start()
    logger.info(
        "Accepting HTTP on PORT=%s — full startup continues in background (GET /health/live)",
        os.environ.get("PORT", "8000"),
    )
    yield
    logger.info("Shutting down %s", get_settings().APP_NAME)


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
_rate_limit_cls = (
    RedisRateLimitMiddleware if settings.use_redis_rate_limit else InMemoryRateLimitMiddleware
)
if settings.use_redis_rate_limit:
    logger.info("Rate limiting: Redis-backed (multi-worker safe)")
else:
    logger.info("Rate limiting: in-memory (single-process)")
app.add_middleware(_rate_limit_cls, requests_per_minute=settings.RATE_LIMIT_PER_MINUTE)
app.add_middleware(TraceMiddleware)

AVATAR_DIR = Path(__file__).resolve().parent.parent / "uploads" / "avatars"
if AVATAR_DIR.exists():
    app.mount("/uploads/avatars", StaticFiles(directory=str(AVATAR_DIR)), name="avatars")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(
        "Unhandled exception while processing request %s %s",
        request.method,
        request.url,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Check backend logs for details."},
        headers=cors_headers_for_request(request),
    )


@app.get("/")
def root():
    return {"message": "OmniAI Backend Running", "environment": settings.ENVIRONMENT}


@app.get("/health/live")
def health_live():
    """Instant liveness probe — no DB/Chroma/LLM calls. Use for Railway health checks."""
    return {"status": "ok", "port": os.environ.get("PORT", "8000")}


@app.get("/health/ready")
def health_ready():
    """Readiness — true after background startup (config validation, migrations) finishes."""
    if getattr(app.state, "startup_error", None):
        return JSONResponse(
            status_code=503,
            content={"status": "error", "detail": app.state.startup_error},
        )
    if not getattr(app.state, "ready", False):
        return JSONResponse(status_code=503, content={"status": "starting"})
    return {"status": "ready"}


@app.get("/health")
def health(
    deep: bool = Query(
        default=False,
        description="When true, probe database, Chroma, and LLM network (may be slow)",
    ),
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
app.include_router(queue_router)
app.include_router(insights_router)
app.include_router(agent_routes.router)
app.include_router(folder_router)
app.include_router(search_router)
