from typing import Optional

from fastapi import FastAPI, Header
from pydantic import BaseModel

from app.client import ask_gpt
from app.config import settings
from app.cost_tracker import CostTracker
from app.rate_limiter import check_rate_limit
from app.token_tracker import TokenTracker


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
    x_user_id: Optional[str] = Header(default="anonymous"),
):
    """
    Main AI Copilot query endpoint.

    Week 2 flow:
    1. Check Redis rate limit.
    2. Send question to the configured LLM.
    3. Extract token usage.
    4. Calculate estimated cost.
    5. Return answer, usage, cost and rate-limit information.
    """

    rate_info = check_rate_limit(user_id=x_user_id)

    result = ask_gpt(request.question)

    usage = TokenTracker.extract_usage(
        {
            "usage": result.get("usage", {})
        }
    )

    cost_info = CostTracker.calculate_cost(
        model=result.get("model", "unknown"),
        prompt_tokens=usage["prompt_tokens"],
        completion_tokens=usage["completion_tokens"],
    )

    return {
        "question": request.question,
        "answer": result.get("answer", ""),
        "model": result.get("model", "unknown"),
        "usage": usage,
        "cost": cost_info,
        "rate_limit": rate_info,
    }