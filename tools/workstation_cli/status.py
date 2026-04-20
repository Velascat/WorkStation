"""
status.py — aggregate_status() produces a structured JSON-serialisable summary
of the whole WorkStation stack.

Output shape (section 4.5):
{
    "overall": "healthy" | "degraded" | "down",
    "timestamp": "<ISO-8601 UTC>",
    "services": {
        "<name>": {
            "healthy": bool,
            "status_code": int | None,
            "latency_ms": float | None,
            "url": str,
            "error": str | None
        },
        ...
    }
}
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Dict

from .health import check_all_health

if TYPE_CHECKING:
    from .services import ServiceConfig


def aggregate_status(services: Dict[str, "ServiceConfig"]) -> dict:
    """
    Check health for all services and return an aggregate status dict.

    Overall status logic:
      - "healthy"  — all services are healthy
      - "degraded" — some (but not all) services are healthy
      - "down"     — no services are healthy
    """
    timestamp = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    health_results = check_all_health(services)

    service_summary: Dict[str, dict] = {}
    for name, result in health_results.items():
        service_summary[name] = {
            "healthy": result["healthy"],
            "status_code": result.get("status_code"),
            "latency_ms": result.get("latency_ms"),
            "url": result.get("url", ""),
            "error": result.get("error"),
        }

    total = len(service_summary)
    healthy_count = sum(1 for s in service_summary.values() if s["healthy"])

    if total == 0:
        overall = "down"
    elif healthy_count == total:
        overall = "healthy"
    elif healthy_count == 0:
        overall = "down"
    else:
        overall = "degraded"

    return {
        "overall": overall,
        "timestamp": timestamp,
        "healthy_count": healthy_count,
        "total_count": total,
        "services": service_summary,
    }
