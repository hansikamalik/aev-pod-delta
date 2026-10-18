
"""
Asset search tool for the AI Gateway.

Provides structured asset search results and citations.
The local asset index is demo data and should later be
replaced by the platform's tenant-scoped RAG search service.
"""

import logging
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings
from app.mock_data import ASSETS
from app.tools import register_tool

logger = logging.getLogger(__name__)


def _search_ai_context(query: str, limit: int = 10) -> Optional[List[Dict[str, Any]]]:
    """Call AI Context's POST /copilot/asset-search.

    Returns a list of assets in the gateway's shape, or None when AI Context
    is not configured or the call fails (the caller then uses local data).
    """
    if not settings.AI_CONTEXT_URL:
        return None

    try:
        response = httpx.post(
            f"{settings.AI_CONTEXT_URL}/copilot/asset-search",
            json={"query": query, "limit": limit},
            timeout=settings.AI_CONTEXT_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
        return [
            {
                "id": item["id"],
                "name": item.get("asset_name"),
                "type": item.get("asset_type"),
                "description": item.get("description"),
                "risk_score": item.get("risk_score"),
                "similarity_score": item.get("similarity_score"),
            }
            for item in payload.get("results", [])
        ]
    except Exception as exc:  # timeout, connection error, bad status, bad JSON
        logger.warning("AI Context asset-search failed, using local data: %s", exc)
        return None


@register_tool("asset_search")
def asset_search(query: str, user_id: str) -> Dict[str, Any]:
    """
    Search assets by name, type, description, or asset ID.

    Args:
        query: Search text.
        user_id: ID of the user making the request.

    Returns:
        A dictionary containing matching assets, result count,
        normalized query, and citations for matching assets.

    Raises:
        TypeError: If query or user_id is not a string.
        ValueError: If query or user_id is empty.
    """

    # Validate query.
    if not isinstance(query, str):
        raise TypeError("query must be a string")

    query = query.strip().lower()
    if not query:
        raise ValueError("query cannot be empty")

    # Validate requesting user.
    if not isinstance(user_id, str):
        raise TypeError("user_id must be a string")

    user_id = user_id.strip()
    if not user_id:
        raise ValueError("user_id must be a non-empty string")

    # Prefer AI Context's vector search; fall back to the local asset index.
    results: List[Dict[str, Any]] = []
    source = "ai_context"
    remote = _search_ai_context(query)

    if remote is not None:
        results = remote
    else:
        source = "local"
        for asset in ASSETS:
            searchable_text = (
                f"{asset['name']} "
                f"{asset['type']} "
                f"{asset['description']} "
                f"{asset['id']}"
            ).lower()

            if query in searchable_text:
                # Return a copy to prevent callers from modifying the index.
                results.append(asset.copy())

    # Generate citations for matching assets.
    citations = [
        {
            "id": f"cit-asset-{asset['id']}",
            "type": "asset",
            "id_ref": asset["id"],
            "url": f"/assets/{asset['id']}",
        }
        for asset in results
    ]

    return {
        "tool": "asset_search",
        "query": query,
        "results": results,
        "count": len(results),
        "citations": citations,
        "source": source,
    }
