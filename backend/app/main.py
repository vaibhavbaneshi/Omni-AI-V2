from fastapi import FastAPI

from backend.app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME
)

@app.get("/")
def root():
    return {
        "app_name": settings.APP_NAME,
        "model": settings.MODEL_NAME
    }

@app.get("/health")
def health():
    return {"status": "healthy"}