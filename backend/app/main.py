from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.user_routes import router as user_router
from app.api.chat_routes import router as chat_router
from app.models.user import User
from app.models.chat_session import ChatSession
from app.models.message import Message
from app.api.upload_routes import (
    router as upload_router
)

from app.api.session_routes import (
    router as session_router
)

from app.api.auth_routes import (
    router as auth_router
)

from app.api.oauth_routes import (
    router as oauth_router
)

from app.api.session_routes import (
    router as session_router
)

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():

    return {
        "message": "OmniAI Backend Running"
    }

@app.get("/health")
def health():

    return {
        "status": "healthy"
    }

# REGISTER ROUTES
app.include_router(user_router)
app.include_router(chat_router)
app.include_router(upload_router)
app.include_router(session_router)
app.include_router(auth_router)
app.include_router(oauth_router)
app.include_router(session_router)