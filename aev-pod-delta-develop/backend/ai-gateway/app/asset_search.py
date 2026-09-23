"""
Asset search tool for the AI Gateway.

Provides a small, structured interface for searching assets
that can later be connected to the platform's RAG asset-search service.
"""

from typing import Any, Dict, List


# Temporary local asset index.
# This keeps the tool deterministic for local development and tests.
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


def asset_search(
    query: str,
    asset_type: str | None = None,
) -> Dict[str, Any]:
    """
    Search for assets and return structured results.

    Args:
        query: Text to search for in asset name or description.
        asset_type: Optional asset type filter.

    Returns:
        A structured dictionary containing matching assets.
    """
    if not isinstance(query, str):
        raise TypeError("query must be a string")

    query = query.strip().lower()

    if not query:
        raise ValueError("query cannot be empty")

    results = []

    for asset in ASSETS:
        if asset_type and asset["type"].lower() != asset_type.lower():
            continue

        searchable_text = (
            f"{asset['name']} "
            f"{asset['type']} "
            f"{asset['description']}"
        ).lower()

        if query in searchable_text:
            results.append(asset.copy())

    return {
        "tool": "asset_search",
        "query": query,
        "results": results,
        "count": len(results),
    }
