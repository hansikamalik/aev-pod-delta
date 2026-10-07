
"""AI Gateway API with guardrails, rate limiting, usage tracking, and tool dispatch."""

import json
import re
from typing import Any, List, Optional

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException
from pydantic import BaseModel

# Import these modules to register their tools.
from app import asset_search, exposure_query, mock_tools  # noqa: F401
from app.audit_log import (  # noqa: F401
    cleanup_expired_rows,
    log_interaction,
    query_interactions,
    setup_database,
    update_fact_check,
)

from app.client import ask_gpt
from app.config import settings
from app.cost_tracker import CostTracker
from app.guardrails import Guardrails
from app.permissions import is_allowed
from app.rate_limiter import check_rate_limit
from app.token_tracker import TokenTracker
from app.tools import dispatch_tool

# Keep setup_database available for tests and optional startup initialization.

app = FastAPI(
    title=getattr(settings, "APP_NAME", "AI Gateway Service"),
    description="AI Gateway Backend for AEV Platform",
    version=getattr(settings, "VERSION", "2.0"),
)

fallback_metrics = {
    "total_requests": 0,
    "fallback_count": 0,
    "fallback_reasons": {},
}


guardrails = Guardrails()
ASSET_ID_PATTERN = re.compile(r"\basset-\d+\b", re.IGNORECASE)


class QueryRequest(BaseModel):
    question: str


class FactCheckRequest(BaseModel):
    interaction_id: str
    fact_check_passed: bool
    details: Optional[str] = None


def _add_citations(target: List[Any], source: Any) -> None:
    """Append citation lists while avoiding duplicate entries."""
    if not isinstance(source, list):
        return

    for citation in source:
        if citation not in target:
            target.append(citation)


def _ensure_risk_score_citation(
    citations: List[Any],
    asset_id: str,
) -> None:
    """Add the standard risk-score citation when the tool provides none."""
    expected_citation = {
        "id": f"cit-risk-{asset_id}",
        "type": "risk_score",
        "id_ref": asset_id,
        "url": f"/risk/{asset_id}",
    }

    if expected_citation not in citations:
        citations.append(expected_citation)


@app.on_event("startup")
def startup_event():
    """Initialize application resources when required."""
    # Database initialization remains disabled to preserve existing behavior.
    # Call setup_database() here when startup database setup is required.
    pass


@app.get("/")
async def root():
    return {"message": "Welcome to AI Gateway Service"}


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "AI Gateway Service",
    }


@app.post("/copilot/query")
def query(
    request: QueryRequest,
    x_user_id: Optional[str] = Header(default="anonymous"),
    x_org_tier: Optional[str] = Header(default="free"),
    x_user_role: Optional[str] = Header(default="anonymous"),
):
    """Process a Copilot query with guardrails, tools, and tracking."""

    rate_info = check_rate_limit(
        user_id=x_user_id,
        org_tier=x_org_tier,
    )

    if not rate_info.get("allowed", False):
        raise HTTPException(
            status_code=429,
            detail={"error": "Rate limit exceeded"},
        )

    input_result = guardrails.process_input(request.question)

    if not input_result["allowed"]:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Request blocked by guardrails",
                "reason": input_result.get("reason", "Input rejected"),
            },
        )

    sanitized_question = input_result["text"]
    question_for_model = sanitized_question
    tool_call = None
    citations: List[Any] = []

    # Dispatch the risk-score tool when an asset ID is mentioned.
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

        asset_id = match.group(0).lower()

        tool_call = dispatch_tool(
            "risk_score_get",
            {"asset_id": asset_id},
            user_id=x_user_id,
            role=x_user_role,
        )

        if isinstance(tool_call, dict) and tool_call.get("ok"):
            tool_result = tool_call.get("result")

            # Collect citations from the dispatcher response.
            _add_citations(citations, tool_call.get("citations", []))

            # Also collect citations from the tool result.
            if isinstance(tool_result, dict):
                _add_citations(
                    citations,
                    tool_result.get("citations", []),
                )

            # Ensure a successful risk-score result has a citation.
            _ensure_risk_score_citation(citations, asset_id)

            question_for_model = (
                f"{sanitized_question}\n\n"
                "Verified data from the risk_score_get tool follows. "
                "Use this data as context for your answer:\n"
                f"{json.dumps(tool_result, default=str)}"
            )

    result = ask_gpt(question_for_model)

    if not isinstance(result, dict):
        result = {
            "answer": str(result),
            "model": "unknown",
        }

    # Preserve citations returned by the LLM client.
    _add_citations(citations, result.get("citations", []))

    usage = TokenTracker.extract_usage(result)

    cost_info = CostTracker.calculate_cost(
        model=result.get("model", "unknown"),
        prompt_tokens=usage["prompt_tokens"],
        completion_tokens=usage["completion_tokens"],
    )

    raw_answer = result.get("answer", "")
    if not isinstance(raw_answer, str):
        raw_answer = str(raw_answer)

    redacted_answer = guardrails.redact_pii(raw_answer)
    output_was_redacted = redacted_answer != raw_answer
    safe_answer = guardrails.process_output(redacted_answer)

    interaction_id = log_interaction(
        user_id=x_user_id,
        prompt=sanitized_question,
        response=safe_answer,
        tokens=usage["total_tokens"],
        cost=cost_info["estimated_cost"],
        citations=citations,
        model=result.get("model", "unknown"),
    )

    fallback_metrics["total_requests"] += 1
    is_fallback = result.get("fallback", False)

    if is_fallback:
        fallback_metrics["fallback_count"] += 1
        reason = result.get("fallback_reason", "unknown")
        reasons = fallback_metrics["fallback_reasons"]
        reasons[reason] = reasons.get(reason, 0) + 1

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
        "fallback_used": is_fallback,
        "fallback_reason": result.get("fallback_reason"),
    }


@app.get("/copilot/audit-log")
def get_audit_log(
    user_id: Optional[str] = None,
    model: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50,
    x_user_role: Optional[str] = Header(default="anonymous"),
):
    """Filter the ai_interactions audit log. Admin/auditor only."""

    if not is_allowed(x_user_role, "audit_query"):
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Permission denied",
                "reason": (
                    f"Role '{x_user_role}' is not permitted "
                    "to read the audit log."
                ),
            },
        )

    rows = query_interactions(
        user_id=user_id,
        model=model,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
    return {"count": len(rows), "results": rows}


@app.post("/webhooks/fact-check")
def fact_check_hook(payload: FactCheckRequest):
    """Record the AI Context fact-check result."""
    update_fact_check(
        payload.interaction_id,
        payload.fact_check_passed,
        payload.details,
    )

    return {
        "status": "success",
        "message": "Fact check result recorded",
    }


@app.post("/admin/retention-cleanup")
def retention_cleanup(background_tasks: BackgroundTasks):
    """Start expired-row cleanup in the background."""
    background_tasks.add_task(cleanup_expired_rows)

    return {
        "status": "success",
        "message": "Retention cleanup job started in background",
    }


@app.get("/metrics/fallback")
def get_fallback_metrics():
    """Return the fallback rate and reason breakdown."""
    total = fallback_metrics["total_requests"]
    fallbacks = fallback_metrics["fallback_count"]
    fallback_rate = fallbacks / total if total > 0 else 0.0

    return {
        "total_requests": total,
        "fallback_count": fallbacks,
        "fallback_rate": fallback_rate,
        "fallback_reasons": fallback_metrics["fallback_reasons"],
    }
