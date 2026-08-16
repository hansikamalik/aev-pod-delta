from typing import Optional

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from app.client import ask_gpt
from app.config import settings
from app.cost_tracker import CostTracker
from app.guardrails import Guardrails
from app.rate_limiter import check_rate_limit
from app.token_tracker import TokenTracker


app = FastAPI(
    title=getattr(settings, "APP_NAME", "AI Gateway Service"),
    description="AI Gateway Backend for AEV Platform",
    version=getattr(settings, "VERSION", "2.0"),
)

guardrails = Guardrails()


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

    Week 3 guardrail flow:
    1. Check rate limit.
    2. Check prompt injection and blocked topics.
    3. Redact input PII.
    4. Send sanitized prompt to the LLM.
    5. Extract token usage.
    6. Calculate estimated cost.
    7. Redact output PII.
    8. Add AI-generated disclaimer.
    9. Enforce maximum response length.
    """

    rate_info = check_rate_limit(user_id=x_user_id)

    input_result = guardrails.process_input(request.question)

    if not input_result["allowed"]:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Request blocked by guardrails",
                "reason": input_result["reason"],
            },
        )

    sanitized_question = input_result["text"]

    result = ask_gpt(sanitized_question)

    usage = TokenTracker.extract_usage(result)

    cost_info = CostTracker.calculate_cost(
        model=result.get("model", "unknown"),
        prompt_tokens=usage["prompt_tokens"],
        completion_tokens=usage["completion_tokens"],
    )

    safe_answer = guardrails.process_output(
        result.get("answer", "")
    )

    return {
        "question": sanitized_question,
        "answer": safe_answer,
        "model": result.get("model", "unknown"),
        "usage": usage,
        "cost": cost_info,
        "rate_limit": rate_info,
        "guardrails": {
            "input_pii_redacted": sanitized_question != request.question,
            "output_pii_redacted": True,
            "disclaimer_added": True,
            "max_output_length": guardrails.max_output_length,
        },
    }
