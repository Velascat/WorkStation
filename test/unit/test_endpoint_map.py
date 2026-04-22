"""
test_endpoint_map.py — Tests for endpoint map loading via config.py.

Verifies that config.load_endpoints() correctly parses endpoints.yaml into
ServiceConfig objects and that the shipped example file is valid.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

import sys
_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools"))

from workstation_cli.config import ServiceConfig, load_endpoints  # noqa: E402


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def endpoints_yaml(tmp_path: Path) -> Path:
    content = textwrap.dedent("""\
        version: "1"

        services:
          switchboard:
            url: "http://localhost:20401"
            health_path: "/health"
            description: "SwitchBoard gateway"

        timeouts:
          connect: 3
          read: 10
    """)
    p = tmp_path / "endpoints.yaml"
    p.write_text(content, encoding="utf-8")
    return p


@pytest.fixture()
def minimal_yaml(tmp_path: Path) -> Path:
    content = textwrap.dedent("""\
        services:
          switchboard:
            url: "http://localhost:20401"
    """)
    p = tmp_path / "endpoints.yaml"
    p.write_text(content, encoding="utf-8")
    return p


# ── Tests: happy path ─────────────────────────────────────────────────────────

class TestLoadEndpoints:
    def test_returns_dict(self, endpoints_yaml: Path):
        result = load_endpoints(endpoints_yaml)
        assert isinstance(result, dict)

    def test_all_services_loaded(self, endpoints_yaml: Path):
        result = load_endpoints(endpoints_yaml)
        assert set(result.keys()) == {"switchboard"}

    def test_returns_service_config_instances(self, endpoints_yaml: Path):
        result = load_endpoints(endpoints_yaml)
        for svc in result.values():
            assert isinstance(svc, ServiceConfig)

    def test_urls_correct(self, endpoints_yaml: Path):
        result = load_endpoints(endpoints_yaml)
        assert result["switchboard"].url == "http://localhost:20401"

    def test_health_path_parsed(self, endpoints_yaml: Path):
        result = load_endpoints(endpoints_yaml)
        for svc in result.values():
            assert svc.health_path == "/health"

    def test_description_parsed(self, endpoints_yaml: Path):
        result = load_endpoints(endpoints_yaml)
        assert "SwitchBoard" in result["switchboard"].description

    def test_timeouts_applied(self, endpoints_yaml: Path):
        result = load_endpoints(endpoints_yaml)
        for svc in result.values():
            assert svc.connect_timeout == 3.0
            assert svc.read_timeout == 10.0

    def test_minimal_file_loads(self, minimal_yaml: Path):
        result = load_endpoints(minimal_yaml)
        assert "switchboard" in result

    def test_minimal_defaults(self, minimal_yaml: Path):
        result = load_endpoints(minimal_yaml)
        svc = result["switchboard"]
        assert svc.health_path == "/health"
        assert svc.description == ""
        assert svc.connect_timeout == 3.0
        assert svc.read_timeout == 10.0

    def test_empty_services_returns_empty_dict(self, tmp_path: Path):
        p = tmp_path / "endpoints.yaml"
        p.write_text("services: {}\n")
        result = load_endpoints(p)
        assert result == {}


# ── Tests: health_url property ────────────────────────────────────────────────

class TestHealthUrl:
    def test_health_url_combines_correctly(self):
        svc = ServiceConfig(name="sb", url="http://localhost:20401", health_path="/health")
        assert svc.health_url == "http://localhost:20401/health"

    def test_health_url_strips_trailing_slash(self):
        svc = ServiceConfig(name="sb", url="http://localhost:20401/", health_path="/health")
        assert svc.health_url == "http://localhost:20401/health"

    def test_health_url_missing_leading_slash(self):
        svc = ServiceConfig(name="sb", url="http://localhost:20401", health_path="health")
        assert svc.health_url == "http://localhost:20401/health"

    def test_health_url_custom_path(self):
        svc = ServiceConfig(name="sb", url="http://localhost:9999", health_path="/api/healthz")
        assert svc.health_url == "http://localhost:9999/api/healthz"

    def test_base_url_alias(self):
        svc = ServiceConfig(name="sb", url="http://localhost:20401")
        assert svc.base_url == svc.url


# ── Tests: error handling ─────────────────────────────────────────────────────

class TestLoadEndpointsErrors:
    def test_missing_file_raises(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            load_endpoints(tmp_path / "does_not_exist.yaml")

    def test_missing_url_raises(self, tmp_path: Path):
        p = tmp_path / "endpoints.yaml"
        p.write_text("services:\n  switchboard:\n    health_path: /health\n")
        with pytest.raises(ValueError, match="missing 'url'"):
            load_endpoints(p)

    def test_non_mapping_root_raises(self, tmp_path: Path):
        p = tmp_path / "endpoints.yaml"
        p.write_text("- just\n- a list\n")
        with pytest.raises(ValueError, match="expected a YAML mapping"):
            load_endpoints(p)


# ── Tests: example file parses correctly ─────────────────────────────────────

class TestExampleFileParses:
    def test_example_file_is_valid(self):
        example = _REPO_ROOT / "config" / "workstation" / "endpoints.example.yaml"
        assert example.exists(), f"Example file missing: {example}"
        result = load_endpoints(example)
        assert len(result) >= 1
        assert "switchboard" in result

    def test_example_switchboard_port(self):
        example = _REPO_ROOT / "config" / "workstation" / "endpoints.example.yaml"
        result = load_endpoints(example)
        assert ":20401" in result["switchboard"].url

    def test_example_contains_only_active_endpoints(self):
        example = _REPO_ROOT / "config" / "workstation" / "endpoints.example.yaml"
        result = load_endpoints(example)
        assert set(result) == {"switchboard", "status"}
