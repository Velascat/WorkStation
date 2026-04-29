# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Velascat
"""
test_stack_health.py — Smoke tests for the running WorkStation stack.

These tests hit real /health endpoints. They are automatically skipped if
the stack is not running, so they are safe to run in any environment.

Run with:
    pytest test/smoke/
    pytest test/smoke/ -v --tb=short
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

try:
    import httpx
    _USE_HTTPX = True
except ImportError:
    import urllib.request
    import urllib.error
    _USE_HTTPX = False

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ENV_FILE = _REPO_ROOT / ".env"


def _load_env() -> dict:
    env: dict = {}
    if _ENV_FILE.exists():
        for line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return env


_ENV = _load_env()


def _port(key: str, default: str) -> str:
    return _ENV.get(key) or os.environ.get(key, default)


PORT_SWITCHBOARD = _port("PORT_SWITCHBOARD", "20401")

SWITCHBOARD_HEALTH_URL = f"http://localhost:{PORT_SWITCHBOARD}/health"

CONNECT_TIMEOUT = 3.0


def _get(url: str) -> tuple[int, str]:
    if _USE_HTTPX:
        resp = httpx.get(url, timeout=CONNECT_TIMEOUT)
        return resp.status_code, resp.text
    else:
        req = urllib.request.Request(url)
        try:
            with urllib.request.urlopen(req, timeout=CONNECT_TIMEOUT) as r:
                return r.status, r.read(2048).decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            return exc.code, ""


def _is_reachable(url: str) -> bool:
    try:
        _get(url)
        return True
    except Exception:
        return False


requires_switchboard = pytest.mark.skipif(
    not _is_reachable(SWITCHBOARD_HEALTH_URL),
    reason=f"SwitchBoard not running at {SWITCHBOARD_HEALTH_URL}",
)


@requires_switchboard
class TestSwitchBoardHealth:
    def test_health_returns_200(self):
        status, body = _get(SWITCHBOARD_HEALTH_URL)
        assert status == 200, f"Expected 200, got {status}. Body: {body[:200]}"

    def test_health_returns_body(self):
        _, body = _get(SWITCHBOARD_HEALTH_URL)
        assert body, "Health endpoint returned an empty body."

    def test_health_url_format(self):
        assert SWITCHBOARD_HEALTH_URL.startswith("http://localhost:")
