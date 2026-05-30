from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.app_settings import configure_langsmith_env, get_settings
from app.core.health import run_health_checks
from app.core.logging_config import setup_logging
from app.api.user_routes import router as user_router
from app.api.chat_routes import router as chat_router
from app.api.upload_routes import router as upload_router
from app.api.session_routes import router as session_router
from app.api.oauth_routes import router as oauth_router
from app.api.memory_routes import router as memory_router
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
    logger.info("Starting %s (%s) llm_provider=%s", settings.APP_NAME, settings.ENVIRONMENT, settings.LLM_PROVIDER)
    health = run_health_checks(probe_llm_network=False)
    logger.info("Startup health: %s", health.get("status"))
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
def health():
    return run_health_checks()


app.include_router(user_router)
app.include_router(chat_router)
app.include_router(upload_router)
app.include_router(session_router)
app.include_router(oauth_router)
app.include_router(memory_router)
