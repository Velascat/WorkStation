# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Velascat
"""
status.py — aggregate_status() produces a structured JSON-serialisable summary
of the whole WorkStation stack.

Output shape:
{
    "platform": "workstation",
    "status": "healthy" | "degraded" | "unhealthy",
    "timestamp": "<ISO-8601 UTC>",
    "services": {
        "<name>": {
            "status": "healthy" | "unhealthy",
            "base_url": str,
            "health_url": str
        },
        ...
    }
}

Health model:
  - "healthy"   — all required services are healthy
  - "degraded"  — all required services are healthy, but optional services are not
  - "unhealthy" — at least one required service is not reachable / not HTTP 200
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Dict

from .health import check_all_health

if TYPE_CHECKING:
    from .config import ServiceConfig


def aggregate_status(services: Dict[str, "ServiceConfig"]) -> dict:
    """
    Check health for all services and return an aggregate status dict.

    Each ServiceConfig carries a ``required`` flag (default: True). Overall
    platform status is determined as follows:

      - "healthy"   — all required services healthy
      - "degraded"  — required services healthy, but one or more optional fail
      - "unhealthy" — any required service is not healthy

    Args:
        services: Mapping of service name to ServiceConfig, as returned by
                  config.load_config() or config.load_endpoints().

    Returns:
        JSON-serialisable dict matching the shape documented above.
    """
    timestamp = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    health_results = check_all_health(services)

    service_summary: Dict[str, dict] = {}
    for name, result in health_results.items():
        svc = services[name]
        service_summary[name] = {
            "status": "healthy" if result["healthy"] else "unhealthy",
            "base_url": svc.base_url,
            "health_url": svc.health_url,
        }

    # Determine platform status based on required flags.
    required_names = {
        name for name, svc in services.items() if getattr(svc, "required", True)
    }

    if not services:
        platform_status = "unhealthy"
    else:
        required_all_healthy = all(
            service_summary[name]["status"] == "healthy"
            for name in required_names
            if name in service_summary
        )
        optional_all_healthy = all(
            service_summary[name]["status"] == "healthy"
            for name in service_summary
            if name not in required_names
        )

        if not required_all_healthy:
            platform_status = "unhealthy"
        elif not optional_all_healthy:
            platform_status = "degraded"
        else:
            platform_status = "healthy"

    return {
        "platform": "workstation",
        "status": platform_status,
        "timestamp": timestamp,
        "services": service_summary,
    }
