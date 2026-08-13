from fastapi import FastAPI, Header
from pydantic import BaseModel
from typing import Optional

from app.config import settings
from app.client import ask_gpt
from app.rate_limiter import check_rate_limit

app = FastAPI(
    title=getattr(settings, "APP_NAME", "AI Gateway Service"),
    description="AI Gateway Backend for AEV Platform",
    version=getattr(settings, "VERSION", "2.0"),
)


class QueryRequest(BaseModel):
    question: str


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


@app.post("/copilot/query")
def query(
    request: QueryRequest,
    x_user_id: Optional[str] = Header(default="anonymous")
):
    """
    Main AI Copilot query endpoint with Week 2 Redis Rate Limiting:
    - Rate limit check (max 5 requests per minute per user)
    - Routes user question to active LLM engine (Gemma 4 / OpenAI / Mock)
    - If over limit -> returns HTTP 429 Too Many Requests
    """
    rate_info = check_rate_limit(user_id=x_user_id)
    answer = ask_gpt(request.question)
    return {
        "question": request.question,
        "answer": answer,
        "rate_limit": rate_info
    }
