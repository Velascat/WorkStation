# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Velascat
"""
health.py — HTTP health-check helpers.

check_health(url) performs a GET request against a service's /health endpoint
and returns a structured dict with the result.

Uses httpx if available (preferred), falls back to urllib from the standard library.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Dict

if TYPE_CHECKING:
    from .config import ServiceConfig


# ── Low-level HTTP check ──────────────────────────────────────────────────────

def check_health(url: str, connect_timeout: float = 3.0, read_timeout: float = 10.0) -> dict:
    """
    Perform a GET request to *url* and return a result dict.

    Return shape:
        {
            "url": str,
            "healthy": bool,
            "status_code": int | None,
            "latency_ms": float | None,   # round-trip time in milliseconds
            "body": str | None,
            "error": str | None,
        }
    """
    result: dict = {
        "url": url,
        "healthy": False,
        "status_code": None,
        "latency_ms": None,
        "body": None,
        "error": None,
    }

    start = time.monotonic()

    try:
        # Prefer httpx for timeout granularity and HTTP/2 support.
        try:
            import httpx

            with httpx.Client(timeout=httpx.Timeout(connect=connect_timeout, read=read_timeout, write=5.0, pool=5.0)) as client:
                response = client.get(url)
            elapsed_ms = (time.monotonic() - start) * 1000
            result["status_code"] = response.status_code
            result["latency_ms"] = round(elapsed_ms, 1)
            result["body"] = response.text[:500]
            result["healthy"] = response.status_code == 200

        except ImportError:
            # Fall back to urllib (stdlib).
            import urllib.request
            import urllib.error

            req = urllib.request.Request(url, method="GET")
            try:
                with urllib.request.urlopen(req, timeout=read_timeout) as resp:
                    elapsed_ms = (time.monotonic() - start) * 1000
                    body = resp.read(500).decode("utf-8", errors="replace")
                    result["status_code"] = resp.status
                    result["latency_ms"] = round(elapsed_ms, 1)
                    result["body"] = body
                    result["healthy"] = resp.status == 200
            except urllib.error.HTTPError as exc:
                elapsed_ms = (time.monotonic() - start) * 1000
                result["status_code"] = exc.code
                result["latency_ms"] = round(elapsed_ms, 1)
                result["error"] = str(exc)
                result["healthy"] = False

    except Exception as exc:  # noqa: BLE001  (catch-all is intentional here)
        elapsed_ms = (time.monotonic() - start) * 1000
        result["latency_ms"] = round(elapsed_ms, 1)
        result["error"] = f"{type(exc).__name__}: {exc}"
        result["healthy"] = False

    return result


# ── Batch check ───────────────────────────────────────────────────────────────

def check_all_health(services: Dict[str, "ServiceConfig"]) -> Dict[str, dict]:
    """
    Run check_health() for every ServiceConfig in *services*.

    Accepts either config.ServiceConfig or services.ServiceConfig objects —
    both expose .health_url, .connect_timeout, and .read_timeout.

    Returns a dict mapping service name -> health result dict.
    """
    results: Dict[str, dict] = {}
    for name, svc in services.items():
        results[name] = check_health(
            url=svc.health_url,
            connect_timeout=svc.connect_timeout,
            read_timeout=svc.read_timeout,
        )
    return results
