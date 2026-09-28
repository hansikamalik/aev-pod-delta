import json
import re
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, BackgroundTasks
from pydantic import BaseModel

from app.citations import router as citations_router
from app.client import ask_gpt
from app.config import settings
from app.cost_tracker import CostTracker
from app.guardrails import Guardrails
from app.permissions import is_allowed
from app.rate_limiter import check_rate_limit
from app.token_tracker import TokenTracker
from app.tools import dispatch_tool
from app import mock_tools  # noqa: F401  (registers the mock tools)
from app.audit_log import (
    setup_database,
    log_interaction,
    update_fact_check,
    cleanup_expired_rows,
)

app = FastAPI(
    title=getattr(settings, "APP_NAME", "AI Gateway Service"),
    description="AI Gateway Backend for AEV Platform",
    version=getattr(settings, "VERSION", "2.0"),
)


@app.on_event("startup")
def startup_event():
    setup_database()


app.include_router(citations_router)


guardrails = Guardrails()

# Demo phase: a question that mentions an asset ID triggers the risk tool.
ASSET_ID_PATTERN = re.compile(r"\basset-\d+\b", re.IGNORECASE)


class QueryRequest(BaseModel):
    question: str


class FactCheckRequest(BaseModel):
    interaction_id: str
    fact_check_passed: bool
    details: Optional[str] = None


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
    x_org_tier: Optional[str] = Header(default="free"),
    x_user_role: Optional[str] = Header(default="anonymous"),
):
    """
    Main AI Copilot query endpoint.
    """

    rate_info = check_rate_limit(user_id=x_user_id, org_tier=x_org_tier)
    if not rate_info["allowed"]:
        raise HTTPException(
            status_code=429,
            detail={"error": "Rate limit exceeded"}
        )

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

    # Tool step (mock data for now): if the question names an asset,
    # fetch its risk score through the RBAC-checked dispatcher.
    tool_call = None
    citations = []
    question_for_model = sanitized_question

    match = ASSET_ID_PATTERN.search(sanitized_question)
    if match:
        if not is_allowed(x_user_role, "risk_score_get"):
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "Permission denied",
                    "reason": (
                        f"Role '{x_user_role}' is not permitted "
                        "to use 'risk_score_get'."
                    ),
                },
            )

        tool_call = dispatch_tool(
            "risk_score_get",
            {"asset_id": match.group(0).lower()},
            user_id=x_user_id,
            role=x_user_role,
        )

        if tool_call["ok"]:
            citations = [tool_call["result"]["citation"]]
            question_for_model = (
                f"{sanitized_question}\n\n"
                "Verified data from the risk_score_get tool "
                "(answer using only this data):\n"
                f"{json.dumps(tool_call['result'])}"
            )

    result = ask_gpt(question_for_model)

    usage = TokenTracker.extract_usage(result)

    cost_info = CostTracker.calculate_cost(
        model=result.get("model", "unknown"),
        prompt_tokens=usage["prompt_tokens"],
        completion_tokens=usage["completion_tokens"],
    )

    raw_answer = result.get("answer", "")
    redacted_answer = guardrails.redact_pii(raw_answer)
    output_was_redacted = redacted_answer != raw_answer

    safe_answer = guardrails.process_output(raw_answer)

    # Week 2: Audit log wiring (Insert row per interaction)
    interaction_id = log_interaction(
        user_id=x_user_id,
        prompt=sanitized_question,
        response=safe_answer,
        tokens=usage["total_tokens"],
        cost=cost_info["estimated_cost"],
        citations=citations
    )

    return {
        "interaction_id": interaction_id,
        "question": sanitized_question,
        "answer": safe_answer,
        "model": result.get("model", "unknown"),
        "usage": usage,
        "tool_call": tool_call,
        "citations": citations,
        "cost": cost_info,
        "rate_limit": rate_info,
        "guardrails": {
            "input_pii_redacted": sanitized_question != request.question,
            "output_pii_redacted": output_was_redacted,
            "disclaimer_added": True,
            "max_output_length": guardrails.max_output_length,
        },
        "fallback_used": result.get("fallback", False),
        "fallback_reason": result.get("fallback_reason"),
    }


@app.post("/webhooks/fact-check")
def fact_check_hook(payload: FactCheckRequest):
    """Week 3: Callback/endpoint AI Context's fact-check pass can call against."""
    update_fact_check(payload.interaction_id, payload.fact_check_passed, payload.details)
    return {"status": "success", "message": "Fact check result recorded"}


@app.post("/admin/retention-cleanup")
def retention_cleanup(background_tasks: BackgroundTasks):
    """Week 2: 1-year retention policy cleanup job for expired rows."""
    background_tasks.add_task(cleanup_expired_rows)
    return {"status": "success", "message": "Retention cleanup job started in background"}
