
"""AI Gateway API with guardrails, rate limiting, usage tracking, and tool dispatch."""

import json
import re
from typing import Optional

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from app import asset_search  # noqa: F401
from app import exposure_query  # noqa: F401
from app import mock_tools  # noqa: F401
from app.client import ask_gpt
from app.config import settings
from app.cost_tracker import CostTracker
from app.guardrails import Guardrails
from app.permissions import is_allowed
from app.rate_limiter import check_rate_limit
from app.token_tracker import TokenTracker
from app.tools import dispatch_tool


app = FastAPI(
    title=getattr(settings, "APP_NAME", "AI Gateway Service"),
    description="AI Gateway Backend for AEV Platform",
    version=getattr(settings, "VERSION", "2.0"),
)

guardrails = Guardrails()

ASSET_ID_PATTERN = re.compile(r"\basset-\d+\b", re.IGNORECASE)


class QueryRequest(BaseModel):
    question: str


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
    x_user_role: Optional[str] = Header(default="anonymous"),
):
    """
    Main AI Copilot query endpoint.

    Processing flow:
    1. Check rate limits.
    2. Apply input guardrails and redact PII.
    3. Detect supported asset IDs and dispatch the risk-score tool.
    4. Include successful tool results in the LLM prompt.
    5. Generate the answer.
    6. Extract token usage and calculate estimated cost.
    7. Apply output guardrails.
    8. Return the answer, tool result, usage, and cost information.
    """

    # Week 3: rate limiting.
    rate_info = check_rate_limit(user_id=x_user_id)

    # Week 3: prompt injection checks, blocked-topic checks, and input PII
    # redaction.
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
    question_for_model = sanitized_question

    tool_call = None
    citations = []

    # Week 4: dispatch the risk-score tool when an asset ID is mentioned.
    # Authorization is checked before dispatching or exposing tool arguments.
    match = ASSET_ID_PATTERN.search(sanitized_question)

    if match:
        if not is_allowed(x_user_role, "risk_score_get"):
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "Tool access denied",
                    "reason": (
                        f"Role '{x_user_role}' is not permitted "
                        "to use tool 'risk_score_get'"
                    ),
                },
            )

        asset_id = match.group(0).lower()

        tool_call = dispatch_tool(
            tool_name="risk_score_get",
            arguments={"asset_id": asset_id},
            user_id=x_user_id,
            role=x_user_role,
        )

        if tool_call["ok"]:
            tool_result = tool_call.get("result")
            citations.extend(tool_call.get("citations", []))

            question_for_model = (
                f"{sanitized_question}\n\n"
                "Verified tool data follows. Use it as context for your answer:\n"
                f"{json.dumps(tool_result, default=str)}"
            )

    # Generate the LLM response. Existing client fallback and mock behavior
    # remain managed by app.client.ask_gpt.
    result = ask_gpt(question_for_model)

    # Week 3: token tracking and cost calculation.
    usage = TokenTracker.extract_usage(result)

    cost_info = CostTracker.calculate_cost(
        model=result.get("model", "unknown"),
        prompt_tokens=usage["prompt_tokens"],
        completion_tokens=usage["completion_tokens"],
    )

    # Preserve citations supplied by the LLM client, when available.
    result_citations = result.get("citations", [])
    if isinstance(result_citations, list):
        citations.extend(result_citations)

    # Week 3: output PII redaction, disclaimer, and output length enforcement.
    raw_answer = result.get("answer", "")
    safe_answer = guardrails.process_output(raw_answer)

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
        "tool_call": tool_call,
        "citations": citations,
    }
