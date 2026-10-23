
from fastapi import FastAPI, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
import hashlib
import hmac
import os
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone
from types import SimpleNamespace

from app.mock_data import get_mock_data
from app.database import engine, Base, get_db
from app.models import AIMemory, Asset, PromptTemplate
from app.schemas import (
    MemoryCreate,
    MemoryUpdate,
    MemoryDelete,
    AssetSearchRequest,
    TemplateCreate,
    TemplateUpdate,
)
from app.embedding import generate_embedding


Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AEV AI Context Service",
    description=(
        "AI Context Service with Memory CRUD, User Isolation, "
        "Memory Types, Template Versioning and Asset Vector Search"
    ),
    version="4.1.0",
)


# --------------------------------------------------
# AUTHENTICATION AND AUTHORIZATION
# --------------------------------------------------

def _configured_api_keys():
    """Load API-key principals without logging secrets."""
    raw = os.getenv("AEV_API_KEYS_JSON", "").strip()
    if not raw:
        return None

    try:
        mapping = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "AEV_API_KEYS_JSON must contain a valid JSON object"
        ) from exc

    if not isinstance(mapping, dict) or not mapping:
        raise RuntimeError(
            "AEV_API_KEYS_JSON must be a non-empty JSON object"
        )

    normalized = {}

    for secret, principal in mapping.items():
        if not isinstance(secret, str) or len(secret) < 32:
            raise RuntimeError(
                "Each API key must be a string of at least 32 characters"
            )

        if (
            not isinstance(principal, dict)
            or not isinstance(principal.get("user_id"), str)
            or not principal["user_id"].strip()
        ):
            raise RuntimeError(
                "Each API key principal must include a non-empty user_id"
            )

        role = principal.get("role", "user")
        if role not in ("user", "admin"):
            raise RuntimeError("API key role must be 'user' or 'admin'")

        tenant_id = principal.get("tenant_id")
        if tenant_id is not None and (
            not isinstance(tenant_id, str) or not tenant_id.strip()
        ):
            raise RuntimeError("tenant_id must be a non-empty string")

        normalized[secret] = {
            "user_id": principal["user_id"],
            "role": role,
            "tenant_id": tenant_id,
        }

    return normalized


def _resolve_principal(request: Request):
    return getattr(request.state, "principal", None)


def _require_admin(request: Request):
    principal = _resolve_principal(request)
    if not principal or principal.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Administrator API key required",
        )
    return principal


def _require_user_match(request: Request, requested_user_id: str):
    principal = _resolve_principal(request)

    if not principal:
        raise HTTPException(status_code=401, detail="Valid API key required")

    if (
        principal.get("role") != "admin"
        and principal.get("user_id") != requested_user_id
    ):
        raise HTTPException(
            status_code=403,
            detail="You may access only your own user data",
        )

    return principal


TENANT_SCOPED_EXACT_PATHS = {
    "/copilot/asset-search",
    "/copilot/executive-summary",
    "/copilot/recommendations",
    "/copilot/freshness-metrics",
}

ADMIN_ONLY_EXACT_PATHS = {
    "/copilot/permission-audit",
    "/copilot/integrations",
}


def _is_tenant_scoped_path(path: str) -> bool:
    if path in TENANT_SCOPED_EXACT_PATHS:
        return True

    prefixes = (
        "/copilot/asset-summary/",
        "/copilot/exposure-explain/",
        "/copilot/remediation-plan/",
        "/assets/",
    )
    return path.startswith(prefixes)


@app.middleware("http")
async def api_key_authentication(request: Request, call_next):
    path = request.url.path

    if path in {"/", "/health", "/docs", "/openapi.json", "/redoc"}:
        return await call_next(request)

    try:
        key_map = _configured_api_keys()
    except RuntimeError:
        from starlette.responses import JSONResponse
        return JSONResponse(
            status_code=500,
            content={"detail": "API authentication configuration is invalid"},
        )

    if key_map is None:
        from starlette.responses import JSONResponse
        return JSONResponse(
            status_code=503,
            content={
                "detail": (
                    "API authentication is not configured; "
                    "set AEV_API_KEYS_JSON before using protected endpoints"
                )
            },
        )

    auth = request.headers.get("Authorization", "")
    scheme, _, presented = auth.partition(" ")

    if scheme.lower() != "bearer" or not presented:
        from starlette.responses import JSONResponse
        return JSONResponse(
            status_code=401,
            content={"detail": "Send Authorization: Bearer <api-key>"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    principal = None
    for known_key, candidate in key_map.items():
        if hmac.compare_digest(presented, known_key):
            principal = candidate

    if principal is None:
        from starlette.responses import JSONResponse
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid API key"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    request.state.principal = principal
    role = principal["role"]

    # Templates and administrative Copilot operations stay admin-only.
    if path.startswith("/templates") or path in ADMIN_ONLY_EXACT_PATHS:
        if role != "admin":
            from starlette.responses import JSONResponse
            return JSONResponse(
                status_code=403,
                content={"detail": "Administrator API key required"},
            )

    # Unknown Copilot/asset routes remain admin-only by default.
    elif path.startswith(("/copilot/", "/assets/")):
        if not _is_tenant_scoped_path(path) and role != "admin":
            from starlette.responses import JSONResponse
            return JSONResponse(
                status_code=403,
                content={"detail": "Administrator API key required"},
            )

        # Tenant-scoped routes require a tenant-bound user key.
        if _is_tenant_scoped_path(path) and role != "admin":
            if not principal.get("tenant_id"):
                from starlette.responses import JSONResponse
                return JSONResponse(
                    status_code=403,
                    content={
                        "detail": "A tenant-bound API key is required"
                    },
                )

    if path == "/memory" and request.method == "GET" and role != "admin":
        from starlette.responses import JSONResponse
        return JSONResponse(
            status_code=403,
            content={
                "detail": (
                    "Administrator API key required to list all users' memories"
                )
            },
        )

    if path.startswith("/memory/user/"):
        requested_id = path.rsplit("/", 1)[-1]
        if role != "admin" and principal["user_id"] != requested_id:
            from starlette.responses import JSONResponse
            return JSONResponse(
                status_code=403,
                content={"detail": "You may access only your own user data"},
            )

    return await call_next(request)


# --------------------------------------------------
# HOME AND HEALTH
# --------------------------------------------------

@app.get("/")
def home():
    return {"message": "Welcome to AEV AI Context Service"}


@app.get("/health")
def health():
    return {"status": "Healthy"}


# --------------------------------------------------
# MEMORY CRUD
# --------------------------------------------------

@app.post("/memory")
def create_memory(
    data: MemoryCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    _require_user_match(request, data.user_id)

    try:
        embedding_vector = generate_embedding(data.conversation)

        new_memory = AIMemory(
            user_id=data.user_id,
            conversation=data.conversation,
            memory_type=data.memory_type,
            embedding=embedding_vector,
        )

        db.add(new_memory)
        db.commit()
        db.refresh(new_memory)

        return {
            "message": "Memory and embedding saved successfully",
            "id": new_memory.id,
            "user_id": new_memory.user_id,
            "conversation": new_memory.conversation,
            "memory_type": new_memory.memory_type,
            "embedding_dimension": len(embedding_vector),
        }

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Memory creation failed; check server logs",
        )


@app.get("/memory")
def get_all_memory(
    request: Request,
    db: Session = Depends(get_db),
):
    _require_admin(request)
    memories = db.query(AIMemory).all()

    return [
        {
            "id": memory.id,
            "user_id": memory.user_id,
            "conversation": memory.conversation,
            "memory_type": memory.memory_type,
            "created_at": memory.created_at,
            "last_used_at": memory.last_used_at,
            "has_embedding": memory.embedding is not None,
        }
        for memory in memories
    ]


@app.get("/memory/user/{user_id}")
def get_user_memory(
    user_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    _require_user_match(request, user_id)

    memories = (
        db.query(AIMemory)
        .filter(AIMemory.user_id == user_id)
        .all()
    )

    return [
        {
            "id": memory.id,
            "user_id": memory.user_id,
            "conversation": memory.conversation,
            "memory_type": memory.memory_type,
            "created_at": memory.created_at,
            "last_used_at": memory.last_used_at,
            "has_embedding": memory.embedding is not None,
        }
        for memory in memories
    ]


@app.put("/memory/{memory_id}")
def update_memory(
    memory_id: int,
    data: MemoryUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    _require_user_match(request, data.user_id)

    memory = (
        db.query(AIMemory)
        .filter(
            AIMemory.id == memory_id,
            AIMemory.user_id == data.user_id,
        )
        .first()
    )

    if memory is None:
        raise HTTPException(
            status_code=404,
            detail="Memory not found for this user",
        )

    try:
        if data.conversation is not None:
            memory.conversation = data.conversation
            memory.embedding = generate_embedding(data.conversation)

        if data.memory_type is not None:
            memory.memory_type = data.memory_type

        memory.last_used_at = func.now()
        db.commit()
        db.refresh(memory)

        return {
            "message": "Memory updated successfully",
            "id": memory.id,
            "user_id": memory.user_id,
            "conversation": memory.conversation,
            "memory_type": memory.memory_type,
        }

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Memory update failed; check server logs",
        )


@app.delete("/memory/{memory_id}")
def delete_memory(
    memory_id: int,
    data: MemoryDelete,
    request: Request,
    db: Session = Depends(get_db),
):
    _require_user_match(request, data.user_id)

    memory = (
        db.query(AIMemory)
        .filter(
            AIMemory.id == memory_id,
            AIMemory.user_id == data.user_id,
        )
        .first()
    )

    if memory is None:
        raise HTTPException(
            status_code=404,
            detail="Memory not found for this user",
        )

    try:
        db.delete(memory)
        db.commit()
        return {"message": "Memory deleted successfully"}

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Memory deletion failed; check server logs",
        )


# --------------------------------------------------
# ASSET DATA SOURCE
# --------------------------------------------------

def _data_source_name():
    source = os.getenv("AEV_DATA_SOURCE", "database").strip().lower()
    return source if source in {"database", "mock"} else "invalid"


def _mock_asset_objects():
    data = get_mock_data()
    score_by_asset = {
        item["asset_id"]: item["score"]
        for item in data["risk_scores"]
    }

    objects = []

    for item in data["assets"]:
        def parse_dt(value):
            return datetime.fromisoformat(value) if value else None

        objects.append(
            SimpleNamespace(
                id=item["id"],
                asset_name=item["asset_name"],
                asset_type=item["asset_type"],
                operating_system=item["operating_system"],
                ip_address=item["ip_address"],
                risk_score=score_by_asset.get(item["id"]),
                description=item["description"],
                visibility=item.get("visibility", "admin_only"),
                owner_user_id=item.get("owner_user_id"),
                tenant_id=item.get("tenant_id"),
                updated_at=parse_dt(item.get("updated_at")),
                embedding_updated_at=parse_dt(
                    item.get("embedding_updated_at")
                ),
                created_at=parse_dt(item.get("updated_at")),
                embedding=[] if item.get("embedding_updated_at") else None,
            )
        )

    return objects


def _all_assets(db: Session):
    source = _data_source_name()

    if source == "mock":
        return _mock_asset_objects()

    if source == "database":
        return db.query(Asset).all()

    raise HTTPException(
        status_code=500,
        detail="AEV_DATA_SOURCE must be 'database' or 'mock'",
    )


def _scope_asset_query(query, principal):
    """Apply authorization before sorting, ranking, limiting or returning."""
    if principal.get("role") == "admin":
        return query

    user_id = principal.get("user_id")
    tenant_id = principal.get("tenant_id")

    if not user_id or not tenant_id:
        raise HTTPException(
            status_code=403,
            detail="User and tenant authorization are required",
        )

    return query.filter(
        Asset.owner_user_id == user_id,
        Asset.tenant_id == tenant_id,
    )


def _assets_for_principal(db: Session, principal: dict):
    """Return only explicitly mapped assets for this principal."""
    source = _data_source_name()

    if source == "mock":
        if principal.get("role") == "admin":
            return _all_assets(db)

        # Mock fixtures are not trusted as tenant ownership records.
        raise HTTPException(
            status_code=403,
            detail="Tenant-scoped access requires the database data source",
        )

    if source != "database":
        raise HTTPException(
            status_code=500,
            detail="AEV_DATA_SOURCE must be 'database' or 'mock'",
        )

    query = _scope_asset_query(db.query(Asset), principal)
    return query.all()


def _asset_for_principal_or_404(
    asset_id: int,
    db: Session,
    principal: dict,
):
    """Return 404 for missing or unauthorized asset IDs."""
    if _data_source_name() == "mock":
        if principal.get("role") == "admin":
            return _asset_or_404(asset_id, db)
        raise HTTPException(status_code=404, detail="Asset not found")

    if _data_source_name() != "database":
        raise HTTPException(
            status_code=500,
            detail="AEV_DATA_SOURCE must be 'database' or 'mock'",
        )

    query = db.query(Asset).filter(Asset.id == asset_id)
    query = _scope_asset_query(query, principal)
    asset = query.first()

    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")

    return asset


def _mock_search_assets(query: str, limit: int):
    terms = [term.lower() for term in query.split() if len(term) > 1]
    matches = []

    for asset in _mock_asset_objects():
        haystack = " ".join(
            str(getattr(asset, field, "") or "")
            for field in (
                "asset_name",
                "asset_type",
                "operating_system",
                "description",
            )
        ).lower()

        overlap = sum(1 for term in terms if term in haystack)
        if overlap:
            matches.append((overlap / max(len(terms), 1), asset))

    matches.sort(
        key=lambda pair: (
            -pair[0],
            -(pair[1].risk_score or 0),
            pair[1].id,
        )
    )
    return matches[:limit]


# --------------------------------------------------
# ASSET SEARCH
# --------------------------------------------------

@app.post("/copilot/asset-search")
def asset_search(
    data: AssetSearchRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    principal = _resolve_principal(request)
    source = _data_source_name()

    try:
        if source == "mock":
            if not principal or principal.get("role") != "admin":
                raise HTTPException(
                    status_code=403,
                    detail="Tenant-scoped access requires the database source",
                )

            ranked = _mock_search_assets(data.query, data.limit)
            results = [
                {
                    "id": asset.id,
                    "asset_name": asset.asset_name,
                    "asset_type": asset.asset_type,
                    "operating_system": asset.operating_system,
                    "ip_address": asset.ip_address,
                    "risk_score": asset.risk_score,
                    "description": asset.description,
                    "similarity_score": round(score, 4),
                    "why_this_matched": _explain_match(data.query, asset),
                }
                for score, asset in ranked
            ]

            return {
                "query": data.query,
                "total_results": len(results),
                "results": results,
                "data_source": "mock",
                "search_mode": (
                    "deterministic_keyword_overlap_not_vector_similarity"
                ),
            }

        if source != "database":
            raise HTTPException(
                status_code=500,
                detail="AEV_DATA_SOURCE must be 'database' or 'mock'",
            )

        if not principal:
            raise HTTPException(status_code=401, detail="Valid API key required")

        query_embedding = generate_embedding(data.query)
        distance = Asset.embedding.cosine_distance(query_embedding)

        # Apply owner + tenant filtering BEFORE ranking and limit.
        query = db.query(Asset, distance.label("distance"))
        query = query.filter(Asset.embedding.is_not(None))
        query = _scope_asset_query(query, principal)

        rows = (
            query.order_by(distance)
            .limit(data.limit)
            .all()
        )

        results = []

        for asset, distance_value in rows:
            similarity_score = 1 - float(distance_value)
            results.append(
                {
                    "id": asset.id,
                    "asset_name": asset.asset_name,
                    "asset_type": asset.asset_type,
                    "operating_system": asset.operating_system,
                    "ip_address": asset.ip_address,
                    "risk_score": asset.risk_score,
                    "description": asset.description,
                    "similarity_score": round(similarity_score, 4),
                    "why_this_matched": _explain_match(data.query, asset),
                }
            )

        return {
            "query": data.query,
            "total_results": len(results),
            "results": results,
            "data_source": "database",
        }

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Asset search failed; check server logs",
        )


# --------------------------------------------------
# COPILOT HELPERS
# --------------------------------------------------

def _asset_or_404(asset_id: int, db: Session):
    source = _data_source_name()

    if source == "mock":
        asset = next(
            (item for item in _mock_asset_objects() if item.id == asset_id),
            None,
        )
    elif source == "database":
        asset = db.query(Asset).filter(Asset.id == asset_id).first()
    else:
        raise HTTPException(
            status_code=500,
            detail="AEV_DATA_SOURCE must be 'database' or 'mock'",
        )

    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")

    return asset


def _asset_facts(asset):
    return {
        "id": asset.id,
        "asset_name": asset.asset_name,
        "asset_type": asset.asset_type,
        "operating_system": asset.operating_system,
        "ip_address": asset.ip_address,
        "risk_score": asset.risk_score,
        "description": asset.description,
        "created_at": (
            asset.created_at.isoformat() if asset.created_at else None
        ),
        "has_embedding": asset.embedding is not None,
    }


def _explain_match(query: str, asset) -> str:
    terms = [term.lower() for term in query.split() if len(term) > 2]
    fields = " ".join(
        str(value or "")
        for value in (
            asset.asset_name,
            asset.asset_type,
            asset.operating_system,
            asset.description,
        )
    ).lower()

    matches = [term for term in terms if term in fields]

    if matches:
        return (
            "Matched query terms in stored asset fields: "
            + ", ".join(matches[:8])
        )

    return (
        "Ranked by vector similarity; no direct query-term overlap "
        "was found in the stored asset fields."
    )


def _gateway_fact_check(facts: dict):
    url = os.getenv("FACT_CHECK_WEBHOOK_URL", "").strip()

    if not url:
        return {
            "status": "not_configured",
            "verified": False,
            "note": (
                "FACT_CHECK_WEBHOOK_URL is not configured; "
                "no external fact check was run."
            ),
        }

    payload = json.dumps(
        {"facts": facts, "source": "aev-ai-context"}
    ).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    token = os.getenv("FACT_CHECK_WEBHOOK_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    outbound_request = urllib.request.Request(
        url,
        data=payload,
        headers=headers,
        method="POST",
    )

    try:
        timeout = float(
            os.getenv("FACT_CHECK_WEBHOOK_TIMEOUT_SECONDS", "3")
        )

        with urllib.request.urlopen(
            outbound_request,
            timeout=timeout,
        ) as response:
            body = response.read(65536).decode(
                "utf-8",
                errors="replace",
            )

        try:
            result = json.loads(body) if body else {}
        except json.JSONDecodeError:
            return {
                "status": "invalid_response",
                "verified": False,
                "note": "Gateway response was not valid JSON.",
            }

        return {
            "status": "completed",
            "verified": bool(result.get("verified", False)),
            "result": result,
            "note": (
                "Gateway output is external and must be reviewed "
                "against its contract."
            ),
        }

    except (urllib.error.URLError, TimeoutError, ValueError):
        return {
            "status": "unavailable",
            "verified": False,
            "note": (
                "External fact check failed; no claim was marked "
                "as verified."
            ),
        }


def _fact_check(facts: dict):
    checked = [
        key
        for key in (
            "asset_name",
            "asset_type",
            "operating_system",
            "ip_address",
            "risk_score",
            "description",
        )
        if facts.get(key) is not None
    ]

    missing = [
        key
        for key in (
            "asset_type",
            "operating_system",
            "ip_address",
            "risk_score",
            "description",
        )
        if facts.get(key) is None
    ]

    return {
        "mode": "database-grounded",
        "verified_claims": [
            {
                "field": key,
                "value": facts[key],
                "source": "assets table",
            }
            for key in checked
        ],
        "unverified_or_missing": missing,
        "note": (
            "Only stored database fields are treated as facts. "
            "External verification is attempted only when "
            "FACT_CHECK_WEBHOOK_URL is configured."
        ),
        "external_check": _gateway_fact_check(facts),
    }


def _freshness_status(asset):
    lag = None
    source_updated_at = getattr(asset, "updated_at", None)
    embedding_updated_at = getattr(asset, "embedding_updated_at", None)

    if source_updated_at is not None and embedding_updated_at is not None:
        try:
            updated_at = source_updated_at
            embedding_at = embedding_updated_at

            if updated_at.tzinfo is None and embedding_at.tzinfo is not None:
                updated_at = updated_at.replace(
                    tzinfo=embedding_at.tzinfo
                )
            elif embedding_at.tzinfo is None and updated_at.tzinfo is not None:
                embedding_at = embedding_at.replace(
                    tzinfo=updated_at.tzinfo
                )

            lag = max(
                0,
                int((embedding_at - updated_at).total_seconds()),
            )
        except (TypeError, ValueError):
            lag = None

    has_embedding = asset.embedding is not None

    if not has_embedding:
        status = "stale_or_missing"
    elif lag is None:
        status = "measurement_unavailable"
    elif lag <= 60:
        status = "within_sla"
    else:
        status = "sla_breached"

    return {
        "has_embedding": has_embedding,
        "freshness_status": status,
        "sla_seconds": 60,
        "measured_lag_seconds": lag,
        "measurement_note": (
            "Lag is calculated from persisted updated_at and "
            "embedding_updated_at timestamps. Existing records need "
            "valid timestamps and a refreshed embedding before lag "
            "is measurable."
        ),
    }


# --------------------------------------------------
# TENANT-SCOPED COPILOT ENDPOINTS
# --------------------------------------------------

@app.get("/copilot/asset-summary/{asset_id}")
def copilot_asset_summary(
    asset_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    asset = _asset_for_principal_or_404(
        asset_id, db, _resolve_principal(request)
    )

    facts = _asset_facts(asset)
    summary = f"{asset.asset_name} is a stored asset record."

    if asset.asset_type:
        summary += f" Type: {asset.asset_type}."
    if asset.operating_system:
        summary += f" Operating system: {asset.operating_system}."
    if asset.risk_score is not None:
        summary += f" Recorded risk score: {asset.risk_score}."
    if asset.description:
        summary += f" Description: {asset.description}"

    return {
        "asset": facts,
        "summary": summary,
        "fact_check": _fact_check(facts),
        "freshness": _freshness_status(asset),
        "data_source": _data_source_name(),
    }


@app.get("/copilot/exposure-explain/{asset_id}")
def copilot_exposure_explain(
    asset_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    asset = _asset_for_principal_or_404(
        asset_id, db, _resolve_principal(request)
    )

    if asset.risk_score is None and not asset.description:
        explanation = (
            "Exposure cannot be assessed from the available record: "
            "risk_score and description are missing."
        )
    else:
        explanation = (
            "This explanation is limited to the stored asset record. "
        )

        if asset.risk_score is not None:
            explanation += (
                f"The recorded risk score is {asset.risk_score}. "
            )
        if asset.description:
            explanation += (
                f"Recorded description: {asset.description} "
            )

        explanation += (
            "No vulnerability scanner, network telemetry, or external "
            "threat-intelligence source was queried."
        )

    response = {
        "asset_id": asset.id,
        "asset_name": asset.asset_name,
        "exposure_explanation": explanation,
        "fact_check": _fact_check(_asset_facts(asset)),
    }

    if _data_source_name() == "mock":
        data = get_mock_data()
        response["exposures"] = [
            item
            for item in data["exposures"]
            if item["asset_id"] == asset.id
        ]
        response["data_source"] = "mock"

    return response


@app.get("/copilot/remediation-plan/{asset_id}")
def copilot_remediation_plan(
    asset_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    asset = _asset_for_principal_or_404(
        asset_id, db, _resolve_principal(request)
    )

    steps = []

    if asset.risk_score is None:
        steps.append({
            "priority": "unknown",
            "action": (
                "Populate and validate the asset risk score "
                "before prioritizing remediation."
            ),
        })
    elif asset.risk_score >= 8:
        steps.append({
            "priority": "high",
            "action": (
                "Validate the high recorded risk score and prioritize "
                "this asset for security review."
            ),
        })
    elif asset.risk_score >= 5:
        steps.append({
            "priority": "medium",
            "action": (
                "Review the recorded risk score and confirm "
                "applicable controls."
            ),
        })
    else:
        steps.append({
            "priority": "normal",
            "action": (
                "Confirm the asset inventory and maintain routine "
                "security controls."
            ),
        })

    if not asset.operating_system:
        steps.append({
            "priority": "normal",
            "action": (
                "Record the operating system and version so patch "
                "guidance can be verified."
            ),
        })
    else:
        steps.append({
            "priority": "normal",
            "action": (
                "Check the vendor's official security advisories for "
                "the recorded operating system and apply approved "
                "patches as applicable."
            ),
        })

    steps.append({
        "priority": "normal",
        "action": (
            "Reassess risk after remediation and update the asset record."
        ),
    })

    return {
        "asset_id": asset.id,
        "asset_name": asset.asset_name,
        "remediation_plan": steps,
        "fact_check": _fact_check(_asset_facts(asset)),
        "note": (
            "Recommendations are generic and must be validated by "
            "the responsible security team; no vulnerability scan "
            "was run."
        ),
    }


@app.get("/copilot/executive-summary")
def copilot_executive_summary(
    request: Request,
    db: Session = Depends(get_db),
):
    assets = _assets_for_principal(
        db, _resolve_principal(request)
    )

    scored = [asset for asset in assets if asset.risk_score is not None]
    high = [asset for asset in scored if asset.risk_score >= 8]
    missing_scores = sum(
        1 for asset in assets if asset.risk_score is None
    )

    return {
        "summary": (
            f"Inventory contains {len(assets)} assets; "
            f"{len(high)} have a recorded risk score of 8 or higher."
        ),
        "metrics": {
            "total_assets": len(assets),
            "assets_with_risk_score": len(scored),
            "assets_missing_risk_score": missing_scores,
            "high_risk_assets_score_8_plus": len(high),
        },
        "high_risk_assets": [
            {
                "id": asset.id,
                "asset_name": asset.asset_name,
                "risk_score": asset.risk_score,
            }
            for asset in high
        ],
        "fact_check": {
            "mode": (
                "database-grounded"
                if _data_source_name() == "database"
                else "mock-data-grounded"
            ),
            "unverified_claims": [],
            "note": (
                "Metrics are computed from the authorized asset scope "
                "only; no external security telemetry was queried."
            ),
        },
        "data_source": _data_source_name(),
    }


@app.get("/copilot/recommendations")
def copilot_recommendations(
    request: Request,
    db: Session = Depends(get_db),
):
    assets = _assets_for_principal(
        db, _resolve_principal(request)
    )

    recommendations = []

    for asset in assets:
        if asset.risk_score is None:
            recommendations.append({
                "asset_id": asset.id,
                "asset_name": asset.asset_name,
                "priority": "unknown",
                "recommendation": "Populate a risk score after assessment.",
            })
        elif asset.risk_score >= 8:
            recommendations.append({
                "asset_id": asset.id,
                "asset_name": asset.asset_name,
                "priority": "high",
                "recommendation": (
                    "Validate risk and schedule a security review."
                ),
            })
        elif asset.risk_score >= 5:
            recommendations.append({
                "asset_id": asset.id,
                "asset_name": asset.asset_name,
                "priority": "medium",
                "recommendation": (
                    "Review controls and confirm risk treatment."
                ),
            })

    return {
        "total_recommendations": len(recommendations),
        "recommendations": recommendations,
        "data_source": _data_source_name(),
        "note": (
            "Rules-based suggestions derived only from the authorized "
            "asset scope's risk scores; not a substitute for "
            "vulnerability analysis."
        ),
    }


# --------------------------------------------------
# UPDATE ASSET
# --------------------------------------------------

@app.patch("/assets/{asset_id}")
def update_asset(
    asset_id: int,
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
):
    if _data_source_name() == "mock":
        raise HTTPException(
            status_code=409,
            detail=(
                "Mock data source is read-only; set "
                "AEV_DATA_SOURCE=database to update persisted assets"
            ),
        )

    asset = _asset_for_principal_or_404(
        asset_id, db, _resolve_principal(request)
    )

    allowed = {
        "asset_name",
        "asset_type",
        "operating_system",
        "ip_address",
        "risk_score",
        "description",
    }

    unknown = set(payload) - allowed
    if unknown:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported fields: {', '.join(sorted(unknown))}",
        )

    if not payload:
        raise HTTPException(
            status_code=400,
            detail="Provide at least one supported field to update",
        )

    try:
        asset.updated_at = datetime.now(timezone.utc)

        for key, value in payload.items():
            setattr(asset, key, value)

        text_for_embedding = " ".join(
            str(getattr(asset, key) or "")
            for key in (
                "asset_name",
                "asset_type",
                "operating_system",
                "description",
            )
        )

        asset.embedding = generate_embedding(text_for_embedding)
        asset.embedding_updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(asset)

        return {
            "message": "Asset updated and embedding refreshed synchronously",
            "asset": _asset_facts(asset),
            "freshness": _freshness_status(asset),
        }

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Asset update failed; check server logs for details",
        )


# --------------------------------------------------
# FRESHNESS METRICS
# --------------------------------------------------

@app.get("/copilot/freshness-metrics")
def copilot_freshness_metrics(
    request: Request,
    db: Session = Depends(get_db),
):
    assets = _assets_for_principal(
        db, _resolve_principal(request)
    )

    statuses = [_freshness_status(asset) for asset in assets]
    measured = [
        item["measured_lag_seconds"]
        for item in statuses
        if item["measured_lag_seconds"] is not None
    ]

    return {
        "total_assets": len(assets),
        "with_embeddings": sum(
            1 for item in statuses if item["has_embedding"]
        ),
        "within_sla": sum(
            1 for item in statuses
            if item["freshness_status"] == "within_sla"
        ),
        "sla_breached": sum(
            1 for item in statuses
            if item["freshness_status"] == "sla_breached"
        ),
        "measurement_unavailable": sum(
            1 for item in statuses
            if item["freshness_status"] == "measurement_unavailable"
        ),
        "stale_or_missing": sum(
            1 for item in statuses
            if item["freshness_status"] == "stale_or_missing"
        ),
        "max_measured_lag_seconds": max(measured) if measured else None,
        "sla_seconds": 60,
        "data_source": _data_source_name(),
        "note": (
            "Authorized-scope snapshot of source timestamps only; "
            "not a historical or load-tested SLA compliance report. "
            "Mock timestamps are illustrative."
        ),
    }


# --------------------------------------------------
# PERMISSION AUDIT (ADMIN ONLY)
# --------------------------------------------------

@app.get("/copilot/permission-audit")
def copilot_permission_audit(request: Request):
    _require_admin(request)

    data = get_mock_data() if _data_source_name() == "mock" else None

    findings = [
        "Protected routes require a configured bearer API key.",
        "Memory CRUD is scoped to the user_id bound to the key.",
        (
            "Assets have owner_user_id and tenant_id columns; legacy "
            "records with NULL mappings are inaccessible to non-admins."
        ),
        (
            "Tenant asset queries filter by owner_user_id and tenant_id "
            "before vector ranking, detail retrieval and aggregate results."
        ),
        (
            "Templates, integrations and permission audit remain admin-only."
        ),
        (
            "Verify cross-tenant negative tests and durable denial audit "
            "logging before production."
        ),
    ]

    result = {
        "status": "tenant_scoping_implemented_pending_verification",
        "result": (
            "Tenant filtering is wired into asset routes. Production "
            "readiness still depends on valid ownership mappings and "
            "passing cross-tenant tests."
        ),
        "findings": findings,
        "required_before_multi_tenant_production": [
            "Populate and verify ownership and tenant mappings for assets.",
            "Run cross-tenant negative tests against the real database.",
            "Verify API-key configuration and role assignment.",
            "Implement durable audit logging for denied access.",
            "Review authorization policy and database migration procedures.",
        ],
        "data_source": _data_source_name(),
    }

    if data is not None:
        result["mock_audit_evidence"] = {
            "asset_count": len(data["assets"]),
            "restricted_asset_count": sum(
                1 for item in data["assets"]
                if item.get("visibility") == "admin_only"
            ),
            "exposure_count": len(data["exposures"]),
            "user_count": len(data["users"]),
            "role_count": len(data["roles"]),
            "integration_count": len(data["integrations"]),
            "denied_events": [
                event for event in data["audit_events"]
                if event.get("outcome") == "denied"
            ],
        }

    return result


# --------------------------------------------------
# INTEGRATIONS (ADMIN ONLY)
# --------------------------------------------------

@app.get("/copilot/integrations")
def copilot_integrations(request: Request):
    _require_admin(request)

    if _data_source_name() == "mock":
        data = get_mock_data()
        return {
            "data_source": "mock",
            "integrations": data["integrations"],
            "note": "Fixtures only; no external integration was contacted.",
        }

    return {
        "data_source": "database",
        "integrations": [],
        "note": "No integration registry is configured for the database provider.",
    }


# --------------------------------------------------
# PROMPT TEMPLATE VERSIONING (ADMIN ONLY)
# --------------------------------------------------

@app.post("/templates/{template_name}/rollback/{version}")
def rollback_template(
    template_name: str,
    version: int,
    request: Request,
    db: Session = Depends(get_db),
):
    _require_admin(request)

    target = (
        db.query(PromptTemplate)
        .filter(
            PromptTemplate.template_name == template_name,
            PromptTemplate.version == version,
        )
        .first()
    )

    if target is None:
        raise HTTPException(
            status_code=404,
            detail="Template version not found",
        )

    try:
        db.query(PromptTemplate).filter(
            PromptTemplate.template_name == template_name
        ).update(
            {PromptTemplate.is_active: False},
            synchronize_session=False,
        )

        target.is_active = True
        db.commit()
        db.refresh(target)

        return {
            "message": "Template rolled back",
            "template_name": template_name,
            "version": target.version,
            "is_active": target.is_active,
        }

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Template rollback failed; check server logs",
        )


@app.get("/templates/{template_name}/route")
def route_template(
    template_name: str,
    request: Request,
    request_id: str = "default",
    db: Session = Depends(get_db),
):
    _require_admin(request)

    versions = (
        db.query(PromptTemplate)
        .filter(
            PromptTemplate.template_name == template_name,
            PromptTemplate.is_active.is_(True),
        )
        .order_by(PromptTemplate.version.asc())
        .all()
    )

    if not versions:
        raise HTTPException(
            status_code=404,
            detail="Template not found",
        )

    bucket = (
        int(hashlib.sha256(request_id.encode("utf-8")).hexdigest()[:8], 16)
        % 100
    )
    selected = versions[bucket % len(versions)]

    return {
        "template_name": template_name,
        "request_id": request_id,
        "bucket": bucket,
        "selected_version": selected.version,
        "template_content": selected.template_content,
        "active_variants": len(versions),
        "routing": "deterministic hash bucket across active variants",
        "note": (
            "Each active version receives an approximately even "
            "deterministic split. This is not a statistically managed "
            "experiment."
        ),
    }


@app.post("/templates")
def create_template(
    data: TemplateCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    _require_admin(request)

    existing = (
        db.query(PromptTemplate)
        .filter(PromptTemplate.template_name == data.template_name)
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=400,
            detail=(
                "Template already exists. Use update endpoint "
                "to create a new version."
            ),
        )

    try:
        template = PromptTemplate(
            template_name=data.template_name,
            version=1,
            template_content=data.template_content,
            is_active=True,
        )

        db.add(template)
        db.commit()
        db.refresh(template)

        return {
            "message": "Template created successfully",
            "id": template.id,
            "template_name": template.template_name,
            "version": template.version,
            "template_content": template.template_content,
            "is_active": template.is_active,
        }

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Template creation failed; check server logs",
        )


@app.put("/templates/{template_name}")
def update_template(
    template_name: str,
    data: TemplateUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    _require_admin(request)

    current_template = (
        db.query(PromptTemplate)
        .filter(
            PromptTemplate.template_name == template_name,
            PromptTemplate.is_active.is_(True),
        )
        .order_by(PromptTemplate.version.desc())
        .first()
    )

    if current_template is None:
        raise HTTPException(
            status_code=404,
            detail="Template not found",
        )

    try:
        new_template = PromptTemplate(
            template_name=template_name,
            version=current_template.version + 1,
            template_content=data.template_content,
            is_active=True,
        )

        db.add(new_template)
        db.commit()
        db.refresh(new_template)

        return {
            "message": "New template version created successfully",
            "template_name": new_template.template_name,
            "version": new_template.version,
            "template_content": new_template.template_content,
            "is_active": new_template.is_active,
        }

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Template update failed; check server logs",
        )


@app.get("/templates/{template_name}/versions")
def get_template_versions(
    template_name: str,
    request: Request,
    db: Session = Depends(get_db),
):
    _require_admin(request)

    templates = (
        db.query(PromptTemplate)
        .filter(PromptTemplate.template_name == template_name)
        .order_by(PromptTemplate.version.asc())
        .all()
    )

    if not templates:
        raise HTTPException(
            status_code=404,
            detail="Template not found",
        )

    return [
        {
            "id": template.id,
            "template_name": template.template_name,
            "version": template.version,
            "template_content": template.template_content,
            "is_active": template.is_active,
            "created_at": template.created_at,
        }
        for template in templates
    ]
