from fastapi import FastAPI, Header
from pydantic import BaseModel
from typing import Optional

try:
    from app.client import ask_gpt
    from app.rate_limiter import check_rate_limit
    from app.pii_guard import check_blocked_topics, redact_pii
except ImportError:
    from client import ask_gpt
    from rate_limiter import check_rate_limit
    from pii_guard import check_blocked_topics, redact_pii

app = FastAPI(title="AI Gateway Service", version="3.0")


class QueryRequest(BaseModel):
    question: str


@app.get("/health")
def health_check():
    """
    Health check endpoint.
    Returns {"status": "ok"} to verify service availability.
    """
    return {"status": "ok", "service": "ai-gateway"}


@app.post("/copilot/query")
def query(
    request: QueryRequest,
    x_user_id: Optional[str] = Header(default="anonymous")
):
    """
    Copilot query endpoint with Enterprise Guardrails:
    1. Rate limit check (max 5 requests per minute per user)
    2. Blocked malicious topics scan (HTTP 400 rejection)
    3. Input PII redaction (<EMAIL_REDACTED>, etc.)
    4. Routes to active LLM engine (Gemma 4 / OpenAI / Mock)
    5. Output PII redaction
    """
    rate_info = check_rate_limit(user_id=x_user_id)

    # Security Guardrails
    check_blocked_topics(request.question)

    safe_question = redact_pii(request.question)
    raw_answer = ask_gpt(safe_question)
    safe_answer = redact_pii(raw_answer)

    return {
        "question": safe_question,
        "answer": safe_answer,
        "rate_limit": rate_info,
        "guardrails_applied": True
    }
