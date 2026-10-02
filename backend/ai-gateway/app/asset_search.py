
"""
Asset search tool for the AI Gateway.

Provides structured asset search results and citations.
The local asset index is demo data and should later be
replaced by the platform's tenant-scoped RAG search service.
"""

from typing import Any, Dict, List

from app.tools import register_tool


# Temporary local asset index for development and tests.
ASSETS: List[Dict[str, Any]] = [
    {
        "id": "asset-001",
        "name": "AI Gateway",
        "type": "service",
        "description": "FastAPI service responsible for AI Copilot requests.",
        "status": "active",
    },
    {
        "id": "asset-002",
        "name": "Redis",
        "type": "database",
        "description": "Redis instance used for request rate limiting.",
        "status": "active",
    },
    {
        "id": "asset-003",
        "name": "PostgreSQL",
        "type": "database",
        "description": "PostgreSQL database used by the platform.",
        "status": "active",
    },
]


@register_tool("asset_search")
def asset_search(query: str, user_id: str) -> Dict[str, Any]:
    """Search assets by name, type, or description."""

    if not isinstance(query, str):
        raise TypeError("query must be a string")

    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("user_id must be a non-empty string")

    query = query.strip().lower()

    if not query:
        raise ValueError("query cannot be empty")

    results = []

    for asset in ASSETS:
        searchable_text = (
            f"{asset['name']} {asset['type']} "
            f"{asset['description']} {asset['id']}"
        ).lower()

        if query in searchable_text:
            results.append(asset.copy())

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
    }
