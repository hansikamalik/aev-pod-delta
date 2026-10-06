"""Report generation tool for the AI Gateway."""

from typing import Any, Dict

from app.tools import register_tool


@register_tool("report_generate")
def report_generate(
    asset_id: str,
    user_id: str,
    report_type: str = "security",
) -> Dict[str, Any]:
    """Generate a structured security report for an asset."""

    if not isinstance(asset_id, str) or not asset_id.strip():
        raise ValueError("asset_id must be a non-empty string")

    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("user_id must be a non-empty string")

    allowed_types = {"security", "risk", "exposure"}

    if report_type not in allowed_types:
        raise ValueError(
            "report_type must be one of: "
            f"{', '.join(sorted(allowed_types))}"
        )

    report_id = f"report-{asset_id}"

    return {
        "tool": "report_generate",
        "report_id": report_id,
        "asset_id": asset_id,
        "report_type": report_type,
        "status": "generated",
        "summary": (
            f"{report_type.capitalize()} report generated "
            f"for asset {asset_id}."
        ),
        "generated_by": user_id,
        "citations": [
            {
                "id": f"cit-report-{asset_id}",
                "type": "report",
                "id_ref": asset_id,
                "url": f"/reports/{report_id}",
            }
        ],
    }
