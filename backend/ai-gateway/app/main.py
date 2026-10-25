
"""AI Gateway API with guardrails, rate limiting, usage tracking, and tool dispatch."""

import json
import logging
import re
from typing import Any, List, Optional

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field

from app.jwt_auth import AuthenticatedUser, get_current_user

# Import these modules to register their tools.
from app import asset_search, exposure_query, mock_tools  # noqa: F401
from app.audit_log import (  # noqa: F401
    cleanup_expired_rows,
    flag_citation,
    log_interaction,
    query_interactions,
    setup_database,
    update_fact_check,
)

from app.citations import router as citations_router, ensure_response_citation
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

app.include_router(citations_router)

fallback_metrics = {
    "total_requests": 0,
    "fallback_count": 0,
    "fallback_reasons": {},
}


logger = logging.getLogger("ai_gateway.main")

guardrails = Guardrails()
ASSET_ID_PATTERN = re.compile(r"\basset-\d+\b", re.IGNORECASE)


class QueryRequest(BaseModel):
    question: str


class FactCheckRequest(BaseModel):
    interaction_id: str
    fact_check_passed: bool
    details: Optional[str] = None


class CitationFlagRequest(BaseModel):
    interaction_id: str = Field(min_length=1, max_length=128)
    citation_id: str = Field(min_length=1, max_length=128)
    reason: str = Field(min_length=1, max_length=1000)


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
    """Initialize the database schema when the application starts."""
    try:
        setup_database()
    except Exception as exc:
        logger.warning(f"Database setup skipped (DB offline): {exc}")


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
    user: AuthenticatedUser = Depends(get_current_user),
    x_user_id: Optional[str] = Header(default=None),
    x_org_tier: Optional[str] = Header(default=None),
    x_user_role: Optional[str] = Header(default=None),
    x_org_id: Optional[str] = Header(default=None),
    x_budget_cap: Optional[float] = Header(default=None),
):
    """Process a Copilot query with guardrails, tools, and tracking."""
    # Identity from cryptographic JWT takes precedence over unverified headers
    eff_user_id = user.user_id if user.token_auth or not x_user_id else x_user_id
    eff_user_role = user.role if user.token_auth or not x_user_role else x_user_role
    eff_org_tier = user.org_tier if user.token_auth or not x_org_tier else x_org_tier
    eff_org_id = user.tenant_id if user.token_auth or not x_org_id else x_org_id
    eff_budget_cap = user.budget_cap if user.budget_cap is not None else x_budget_cap

    rate_info = check_rate_limit(
        user_id=eff_user_id,
        org_tier=eff_org_tier,
    )

    if not rate_info.get("allowed", False):
        raise HTTPException(
            status_code=429,
            detail={"error": "Rate limit exceeded"},
        )

    raw_question = request.question.strip()
    if not raw_question:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Validation error",
                "message": "Question cannot be empty or whitespace only",
            },
        )

    if len(request.question) > 8000:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Payload too large",
                "message": "Question exceeds maximum allowed length of 8000 characters",
            },
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

    sanitized_question = input_result["text"].strip()
    if not sanitized_question:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Validation error",
                "message": "Question cannot be empty after sanitization",
            },
        )

    question_for_model = sanitized_question
    tool_call = None
    citations: List[Any] = []

    # Dynamic Tool Reasoning & Routing
    from app.tool_router import resolve_dynamic_tool_intent, get_gemini_tools

    tool_intent = resolve_dynamic_tool_intent(sanitized_question)

    if tool_intent is not None:
        target_tool, tool_args = tool_intent

        if not is_allowed(eff_user_role, target_tool):
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "Permission denied",
                    "reason": (
                        f"Role '{eff_user_role}' is not permitted "
                        f"to use '{target_tool}'."
                    ),
                },
            )

        tool_call = dispatch_tool(
            target_tool,
            tool_args,
            user_id=eff_user_id,
            role=eff_user_role,
        )

        if isinstance(tool_call, dict):
            _add_citations(citations, tool_call.get("citations", []))

            if tool_call.get("ok"):
                tool_result = tool_call.get("result")

                if isinstance(tool_result, dict):
                    _add_citations(
                        citations,
                        tool_result.get("citations", []),
                    )

                if target_tool == "risk_score_get":
                    asset_id = tool_args.get("asset_id", "")
                    _ensure_risk_score_citation(citations, asset_id)

                question_for_model = (
                    f"{sanitized_question}\n\n"
                    f"Verified data from the {target_tool} tool follows. "
                    "Use this data as context for your answer:\n"
                    f"{json.dumps(tool_result, default=str)}"
                )

    try:
        import inspect
        sig = inspect.signature(ask_gpt)
        if "tools" in sig.parameters or any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
            tools_decl = [get_gemini_tools()] if get_gemini_tools() else None
            result = ask_gpt(question_for_model, tools=tools_decl)
        else:
            result = ask_gpt(question_for_model)
    except Exception as exc:
        logger.error(f"Upstream model execution failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=502,
            detail={
                "error": "Upstream model failure",
                "message": "Upstream model failure",
            },
        )

    if not isinstance(result, dict):
        result = {
            "answer": str(result),
            "model": "unknown",
        }

    # Preserve citations returned by the LLM client.
    _add_citations(citations, result.get("citations", []))

    usage = TokenTracker.extract_usage(result)

    # Map request to organization: prefer verified tenant/org, else user_id or org_tier
    effective_org = eff_org_id
    if not effective_org and eff_user_id:
        if "@" in eff_user_id:
            effective_org = eff_user_id.split("@", 1)[1]
        elif "_" in eff_user_id and "org" in eff_user_id:
            effective_org = eff_user_id.split("_", 1)[1]
    if not effective_org:
        effective_org = eff_org_tier or "default"

    cost_info = CostTracker.calculate_cost(
        model=result.get("model", "unknown"),
        prompt_tokens=usage["prompt_tokens"],
        completion_tokens=usage["completion_tokens"],
        budget_cap=eff_budget_cap,
        org_id=effective_org,
    )

    raw_answer = result.get("answer", "")
    if not isinstance(raw_answer, str):
        raw_answer = str(raw_answer)

    redacted_answer = guardrails.redact_pii(raw_answer)
    output_was_redacted = redacted_answer != raw_answer
    safe_answer = guardrails.process_output(redacted_answer)

    # Ensure every response carries at least one verified citation
    citations = ensure_response_citation(citations, sanitized_question, safe_answer)

    interaction_id = log_interaction(
        user_id=eff_user_id,
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
    limit: int = Query(default=50, ge=1, le=500),
    user: AuthenticatedUser = Depends(get_current_user),
    x_user_role: Optional[str] = Header(default=None),
):
    """Filter the ai_interactions audit log. Admin/auditor only."""
    effective_role = user.role if user.token_auth or not x_user_role else x_user_role

    if not is_allowed(effective_role, "audit_query"):
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Permission denied",
                "reason": (
                    f"Role '{effective_role}' is not permitted "
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


@app.post("/copilot/citations/flag")
def flag_citation_endpoint(
    payload: CitationFlagRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    x_user_id: Optional[str] = Header(default=None),
    x_user_role: Optional[str] = Header(default=None),
):
    """Record a user flag marking a citation as inaccurate."""
    effective_role = user.role if user.token_auth or not x_user_role else x_user_role
    effective_user = user.user_id if user.token_auth or not x_user_id else x_user_id

    if not is_allowed(effective_role, "citation_flag"):
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Permission denied",
                "reason": (
                    f"Role '{effective_role}' is not permitted "
                    "to flag citations."
                ),
            },
        )

    flag_citation(
        interaction_id=payload.interaction_id,
        citation_id=payload.citation_id,
        reason=payload.reason,
        flagged_by=effective_user or "anonymous",
    )

    return {
        "status": "success",
        "message": "Citation flag recorded",
    }


@app.post("/admin/retention-cleanup")
def retention_cleanup(
    background_tasks: BackgroundTasks,
    user: AuthenticatedUser = Depends(get_current_user),
    x_user_role: Optional[str] = Header(default=None),
):
    """Start expired-row cleanup in the background. Admin only."""
    effective_role = user.role if user.token_auth or not x_user_role else x_user_role

    if effective_role != "admin":
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Permission denied",
                "reason": (
                    f"Role '{effective_role}' is not permitted "
                    "to run retention cleanup."
                ),
            },
        )

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
