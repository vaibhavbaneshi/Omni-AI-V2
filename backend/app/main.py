from fastapi import FastAPI
from app.core.config import settings
from app.api.user_routes import router as user_router
from app.api.chat_routes import router as chat_router
from app.models.user import User
from app.models.chat_session import ChatSession
from app.models.message import Message
from app.api.upload_routes import (
    router as upload_router
)

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0"
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