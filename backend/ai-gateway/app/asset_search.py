
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

    # Search the local asset index.
    results: List[Dict[str, Any]] = []

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
    }
