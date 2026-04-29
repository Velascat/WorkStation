# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Velascat
"""
test_endpoint_config.py — Unit tests for endpoint config parsing.

These tests do not require the stack to be running. They verify that
services.py correctly parses endpoints.yaml files and rejects malformed input.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

# ── Make sure the package is importable from the repo root ───────────────────
import sys
_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools"))

from workstation_cli.config import ServiceConfig, load_endpoints as load_services_from_yaml  # noqa: E402


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def valid_endpoints_yaml(tmp_path: Path) -> Path:
    """Write a valid endpoints.yaml to a temp file and return its path."""
    content = textwrap.dedent("""\
        version: "1"

        services:
          switchboard:
            url: "http://localhost:20401"
            health_path: "/health"
            description: "SwitchBoard gateway"
          status:
            url: "http://localhost:20400"
            health_path: "/health"
            description: "Status API"

        timeouts:
          connect: 3
          read: 10
    """)
    p = tmp_path / "endpoints.yaml"
    p.write_text(content, encoding="utf-8")
    return p


@pytest.fixture()
def minimal_endpoints_yaml(tmp_path: Path) -> Path:
    """Minimal valid file — only required fields."""
    content = textwrap.dedent("""\
        services:
          switchboard:
            url: "http://localhost:20401"
    """)
    p = tmp_path / "endpoints.yaml"
    p.write_text(content, encoding="utf-8")
    return p


# ── Tests: happy path ─────────────────────────────────────────────────────────

class TestLoadServicesFromYaml:
    def test_returns_dict(self, valid_endpoints_yaml: Path):
        services = load_services_from_yaml(valid_endpoints_yaml)
        assert isinstance(services, dict)

    def test_all_services_loaded(self, valid_endpoints_yaml: Path):
        services = load_services_from_yaml(valid_endpoints_yaml)
        assert set(services.keys()) == {"switchboard", "status"}

    def test_service_is_serviceconfig_instance(self, valid_endpoints_yaml: Path):
        services = load_services_from_yaml(valid_endpoints_yaml)
        for svc in services.values():
            assert isinstance(svc, ServiceConfig)

    def test_url_parsed_correctly(self, valid_endpoints_yaml: Path):
        services = load_services_from_yaml(valid_endpoints_yaml)
        assert services["switchboard"].url == "http://localhost:20401"
        assert services["status"].url == "http://localhost:20400"

    def test_health_path_parsed(self, valid_endpoints_yaml: Path):
        services = load_services_from_yaml(valid_endpoints_yaml)
        for svc in services.values():
            assert svc.health_path == "/health"

    def test_description_parsed(self, valid_endpoints_yaml: Path):
        services = load_services_from_yaml(valid_endpoints_yaml)
        assert "SwitchBoard" in services["switchboard"].description

    def test_timeouts_applied(self, valid_endpoints_yaml: Path):
        services = load_services_from_yaml(valid_endpoints_yaml)
        for svc in services.values():
            assert svc.connect_timeout == 3.0
            assert svc.read_timeout == 10.0

    def test_minimal_yaml_loads(self, minimal_endpoints_yaml: Path):
        """A file with only url should load without error."""
        services = load_services_from_yaml(minimal_endpoints_yaml)
        assert "switchboard" in services

    def test_minimal_defaults(self, minimal_endpoints_yaml: Path):
        """Absent optional fields should fall back to defaults."""
        services = load_services_from_yaml(minimal_endpoints_yaml)
        svc = services["switchboard"]
        assert svc.health_path == "/health"
        assert svc.description == ""
        assert svc.connect_timeout == 3.0
        assert svc.read_timeout == 10.0


# ── Tests: ServiceConfig.health_url ──────────────────────────────────────────

class TestServiceConfigHealthUrl:
    def test_health_url_combines_url_and_path(self):
        svc = ServiceConfig(name="switchboard", url="http://localhost:20401", health_path="/health")
        assert svc.health_url == "http://localhost:20401/health"

    def test_health_url_strips_trailing_slash_from_url(self):
        svc = ServiceConfig(name="switchboard", url="http://localhost:20401/", health_path="/health")
        assert svc.health_url == "http://localhost:20401/health"

    def test_health_url_handles_missing_leading_slash_in_path(self):
        svc = ServiceConfig(name="switchboard", url="http://localhost:20401", health_path="health")
        assert svc.health_url == "http://localhost:20401/health"

    def test_health_url_custom_path(self):
        svc = ServiceConfig(name="custom", url="http://localhost:9999", health_path="/api/healthz")
        assert svc.health_url == "http://localhost:9999/api/healthz"


# ── Tests: error handling ─────────────────────────────────────────────────────

class TestLoadServicesErrors:
    def test_missing_file_raises_file_not_found(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            load_services_from_yaml(tmp_path / "does_not_exist.yaml")

    def test_missing_url_raises_value_error(self, tmp_path: Path):
        content = textwrap.dedent("""\
            services:
              switchboard:
                health_path: "/health"
        """)
        p = tmp_path / "bad.yaml"
        p.write_text(content)
        with pytest.raises(ValueError, match="missing 'url'"):
            load_services_from_yaml(p)

    def test_non_mapping_root_raises_value_error(self, tmp_path: Path):
        p = tmp_path / "bad.yaml"
        p.write_text("- just a list\n- not a mapping\n")
        with pytest.raises(ValueError, match="expected a YAML mapping"):
            load_services_from_yaml(p)

    def test_empty_services_returns_empty_dict(self, tmp_path: Path):
        content = "services: {}\n"
        p = tmp_path / "empty.yaml"
        p.write_text(content)
        services = load_services_from_yaml(p)
        assert services == {}


# ── Tests: example file parses correctly ─────────────────────────────────────

class TestExampleFileParses:
    """Verify that the shipped example file is valid and parseable."""

    def test_example_endpoints_yaml_is_valid(self):
        example = _REPO_ROOT / "config" / "workstation" / "endpoints.example.yaml"
        assert example.exists(), f"Example file not found: {example}"
        services = load_services_from_yaml(example)
        assert len(services) >= 1, "Expected at least switchboard."
        assert "switchboard" in services

    def test_example_switchboard_port(self):
        example = _REPO_ROOT / "config" / "workstation" / "endpoints.example.yaml"
        services = load_services_from_yaml(example)
        assert ":20401" in services["switchboard"].url

    def test_example_contains_only_active_services(self):
        example = _REPO_ROOT / "config" / "workstation" / "endpoints.example.yaml"
        services = load_services_from_yaml(example)
        assert set(services) == {"switchboard", "status"}
