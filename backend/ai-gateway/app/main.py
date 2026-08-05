from fastapi import FastAPI
from app.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    description="AI Gateway Backend for AEV Platform",
    version=settings.VERSION,
)


@app.get("/")
async def root():
    return {
        "message": "Welcome to AI Gateway Service"
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "AI Gateway Service"
    }