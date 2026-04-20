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

# ── Try to import an HTTP client ──────────────────────────────────────────────
try:
    import httpx
    _USE_HTTPX = True
except ImportError:
    import urllib.request
    import urllib.error
    _USE_HTTPX = False

# ── Configuration ─────────────────────────────────────────────────────────────

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ENV_FILE = _REPO_ROOT / ".env"


def _load_env() -> dict:
    """Parse .env file into a dict. Falls back to OS environment."""
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
PORT_9ROUTER = _port("PORT_9ROUTER", "20128")

SWITCHBOARD_HEALTH_URL = f"http://localhost:{PORT_SWITCHBOARD}/health"
NINEROUTER_HEALTH_URL = f"http://localhost:{PORT_9ROUTER}/health"

CONNECT_TIMEOUT = 3.0


# ── Helper ─────────────────────────────────────────────────────────────────────

def _get(url: str) -> tuple[int, str]:
    """GET *url* and return (status_code, body). Raises on connection error."""
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
    """Return True if the service responds to a GET request."""
    try:
        status, _ = _get(url)
        return True
    except Exception:
        return False


# ── Skip markers ──────────────────────────────────────────────────────────────

requires_switchboard = pytest.mark.skipif(
    not _is_reachable(SWITCHBOARD_HEALTH_URL),
    reason=f"SwitchBoard not running at {SWITCHBOARD_HEALTH_URL}",
)

requires_9router = pytest.mark.skipif(
    not _is_reachable(NINEROUTER_HEALTH_URL),
    reason=f"9router not running at {NINEROUTER_HEALTH_URL}",
)

requires_full_stack = pytest.mark.skipif(
    not (_is_reachable(SWITCHBOARD_HEALTH_URL) and _is_reachable(NINEROUTER_HEALTH_URL)),
    reason="Full stack (SwitchBoard + 9router) not running",
)


# ── Tests ─────────────────────────────────────────────────────────────────────

@requires_switchboard
class TestSwitchBoardHealth:
    def test_health_returns_200(self):
        """SwitchBoard /health must return HTTP 200."""
        status, body = _get(SWITCHBOARD_HEALTH_URL)
        assert status == 200, f"Expected 200, got {status}. Body: {body[:200]}"

    def test_health_returns_json_body(self):
        """SwitchBoard /health response should be non-empty."""
        _, body = _get(SWITCHBOARD_HEALTH_URL)
        assert body, "Health endpoint returned an empty body."

    def test_health_url_format(self):
        """Health URL should be well-formed."""
        assert SWITCHBOARD_HEALTH_URL.startswith("http://localhost:")


@requires_9router
class TestNineRouterHealth:
    def test_health_returns_200(self):
        """9router /health must return HTTP 200."""
        status, body = _get(NINEROUTER_HEALTH_URL)
        assert status == 200, f"Expected 200, got {status}. Body: {body[:200]}"

    def test_health_returns_json_body(self):
        """9router /health response should be non-empty."""
        _, body = _get(NINEROUTER_HEALTH_URL)
        assert body, "Health endpoint returned an empty body."


@requires_full_stack
class TestFullStackConnectivity:
    def test_both_services_healthy(self):
        """Both SwitchBoard and 9router must return HTTP 200 simultaneously."""
        sb_status, _ = _get(SWITCHBOARD_HEALTH_URL)
        nr_status, _ = _get(NINEROUTER_HEALTH_URL)
        assert sb_status == 200, f"SwitchBoard unhealthy: HTTP {sb_status}"
        assert nr_status == 200, f"9router unhealthy: HTTP {nr_status}"

    def test_switchboard_reachable_from_host(self):
        """SwitchBoard should accept connections on the expected host port."""
        assert _is_reachable(SWITCHBOARD_HEALTH_URL), (
            f"Cannot reach SwitchBoard at {SWITCHBOARD_HEALTH_URL}"
        )

    def test_9router_reachable_from_host(self):
        """9router should accept connections on the expected host port."""
        assert _is_reachable(NINEROUTER_HEALTH_URL), (
            f"Cannot reach 9router at {NINEROUTER_HEALTH_URL}"
        )
