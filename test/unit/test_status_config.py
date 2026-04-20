"""
test_status_config.py — Tests for status aggregation and config loading.

Covers:
  - config.load_config() merging endpoints + services meta
  - config.load_services_meta() required/optional flags
  - config.load_ports()
  - status.aggregate_status() healthy / degraded / unhealthy logic
  - Missing-config behaviour (FileNotFoundError, graceful degradation)
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest

import sys
_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools"))

from workstation_cli.config import (  # noqa: E402
    ServiceConfig,
    WorkstationConfig,
    load_config,
    load_endpoints,
    load_ports,
    load_services_meta,
)
from workstation_cli.status import aggregate_status  # noqa: E402


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _write(path: Path, text: str) -> Path:
    path.write_text(textwrap.dedent(text), encoding="utf-8")
    return path


@pytest.fixture()
def config_dir(tmp_path: Path) -> Path:
    """A temporary config/workstation directory with all three YAML files."""
    d = tmp_path / "workstation"
    d.mkdir()

    _write(d / "endpoints.yaml", """\
        version: "1"
        services:
          switchboard:
            url: "http://localhost:20401"
            health_path: "/health"
            description: "SwitchBoard gateway"
          ninerouter:
            url: "http://localhost:20128"
            health_path: "/health"
            description: "9router dispatcher"
          metrics:
            url: "http://localhost:9090"
            health_path: "/health"
            description: "Optional metrics"
        timeouts:
          connect: 3
          read: 10
    """)

    _write(d / "services.yaml", """\
        services:
          - name: switchboard
            required: true
          - name: ninerouter
            required: true
          - name: metrics
            required: false
    """)

    _write(d / "ports.yaml", """\
        ports:
          switchboard: 20401
          ninerouter: 20128
    """)

    return d


@pytest.fixture()
def endpoints_only_dir(tmp_path: Path) -> Path:
    """A directory with only endpoints.yaml (no services.yaml or ports.yaml)."""
    d = tmp_path / "workstation"
    d.mkdir()
    _write(d / "endpoints.yaml", """\
        services:
          switchboard:
            url: "http://localhost:20401"
          ninerouter:
            url: "http://localhost:20128"
    """)
    return d


# ── Tests: load_services_meta ─────────────────────────────────────────────────

class TestLoadServicesMeta:
    def test_parses_required_flags(self, tmp_path: Path):
        p = _write(tmp_path / "services.yaml", """\
            services:
              - name: switchboard
                required: true
              - name: 9router
                required: true
        """)
        meta = load_services_meta(p)
        assert meta["switchboard"]["required"] is True
        assert meta["9router"]["required"] is True

    def test_optional_flag(self, tmp_path: Path):
        p = _write(tmp_path / "services.yaml", """\
            services:
              - name: metrics
                required: false
        """)
        meta = load_services_meta(p)
        assert meta["metrics"]["required"] is False

    def test_missing_file_raises(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            load_services_meta(tmp_path / "nope.yaml")

    def test_non_list_services_raises(self, tmp_path: Path):
        p = _write(tmp_path / "services.yaml", "services:\n  switchboard: true\n")
        with pytest.raises(ValueError, match="must be a list"):
            load_services_meta(p)

    def test_example_file_parses(self):
        example = _REPO_ROOT / "config" / "workstation" / "services.example.yaml"
        assert example.exists(), f"Missing: {example}"
        meta = load_services_meta(example)
        assert "switchboard" in meta
        assert "9router" in meta
        assert meta["switchboard"]["required"] is True
        assert meta["9router"]["required"] is True


# ── Tests: load_ports ─────────────────────────────────────────────────────────

class TestLoadPorts:
    def test_parses_ports(self, tmp_path: Path):
        p = _write(tmp_path / "ports.yaml", """\
            ports:
              switchboard: 20401
              ninerouter: 20128
        """)
        ports = load_ports(p)
        assert ports["switchboard"] == 20401
        assert ports["ninerouter"] == 20128

    def test_missing_file_raises(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            load_ports(tmp_path / "nope.yaml")

    def test_example_file_parses(self):
        example = _REPO_ROOT / "config" / "workstation" / "ports.example.yaml"
        assert example.exists(), f"Missing: {example}"
        ports = load_ports(example)
        assert ports.get("switchboard") == 20401
        assert ports.get("9router") == 20128


# ── Tests: load_config ────────────────────────────────────────────────────────

class TestLoadConfig:
    def test_returns_workstation_config(self, config_dir: Path):
        cfg = load_config(config_dir)
        assert isinstance(cfg, WorkstationConfig)

    def test_services_loaded(self, config_dir: Path):
        cfg = load_config(config_dir)
        assert "switchboard" in cfg.services
        assert "ninerouter" in cfg.services
        assert "metrics" in cfg.services

    def test_required_flags_merged(self, config_dir: Path):
        cfg = load_config(config_dir)
        assert cfg.services["switchboard"].required is True
        assert cfg.services["ninerouter"].required is True
        assert cfg.services["metrics"].required is False

    def test_ports_loaded(self, config_dir: Path):
        cfg = load_config(config_dir)
        assert cfg.ports["switchboard"] == 20401
        assert cfg.ports["ninerouter"] == 20128

    def test_endpoints_only_defaults_to_required(self, endpoints_only_dir: Path):
        """When services.yaml is absent all services default to required=True."""
        cfg = load_config(endpoints_only_dir)
        for svc in cfg.services.values():
            assert svc.required is True

    def test_endpoints_only_empty_ports(self, endpoints_only_dir: Path):
        cfg = load_config(endpoints_only_dir)
        assert cfg.ports == {}

    def test_missing_endpoints_raises(self, tmp_path: Path):
        d = tmp_path / "workstation"
        d.mkdir()
        with pytest.raises(FileNotFoundError):
            load_config(d)


# ── Tests: aggregate_status ───────────────────────────────────────────────────

def _make_services(specs: dict) -> dict:
    """
    Build a dict of ServiceConfig from a compact spec dict.

    specs: {name: {"url": ..., "required": bool}}
    """
    return {
        name: ServiceConfig(
            name=name,
            url=v["url"],
            required=v.get("required", True),
        )
        for name, v in specs.items()
    }


def _mock_health(healthy_names: set):
    """Return a patch for check_all_health that marks named services healthy."""
    def _fake(services):
        return {
            name: {
                "healthy": name in healthy_names,
                "status_code": 200 if name in healthy_names else None,
                "latency_ms": 5.0 if name in healthy_names else None,
                "url": svc.health_url,
                "error": None if name in healthy_names else "Connection refused",
            }
            for name, svc in services.items()
        }
    return _fake


class TestAggregateStatus:

    def test_all_required_healthy_is_healthy(self):
        services = _make_services({
            "switchboard": {"url": "http://localhost:20401", "required": True},
            "ninerouter":  {"url": "http://localhost:20128", "required": True},
        })
        with patch("workstation_cli.status.check_all_health",
                   side_effect=_mock_health({"switchboard", "ninerouter"})):
            result = aggregate_status(services)
        assert result["status"] == "healthy"

    def test_required_failing_is_unhealthy(self):
        services = _make_services({
            "switchboard": {"url": "http://localhost:20401", "required": True},
            "ninerouter":  {"url": "http://localhost:20128", "required": True},
        })
        with patch("workstation_cli.status.check_all_health",
                   side_effect=_mock_health({"ninerouter"})):
            result = aggregate_status(services)
        assert result["status"] == "unhealthy"

    def test_optional_failing_required_ok_is_degraded(self):
        services = _make_services({
            "switchboard": {"url": "http://localhost:20401", "required": True},
            "ninerouter":  {"url": "http://localhost:20128", "required": True},
            "metrics":     {"url": "http://localhost:9090",  "required": False},
        })
        with patch("workstation_cli.status.check_all_health",
                   side_effect=_mock_health({"switchboard", "ninerouter"})):
            result = aggregate_status(services)
        assert result["status"] == "degraded"

    def test_all_unhealthy_is_unhealthy(self):
        services = _make_services({
            "switchboard": {"url": "http://localhost:20401", "required": True},
            "ninerouter":  {"url": "http://localhost:20128", "required": True},
        })
        with patch("workstation_cli.status.check_all_health",
                   side_effect=_mock_health(set())):
            result = aggregate_status(services)
        assert result["status"] == "unhealthy"

    def test_empty_services_is_unhealthy(self):
        with patch("workstation_cli.status.check_all_health", return_value={}):
            result = aggregate_status({})
        assert result["status"] == "unhealthy"

    def test_output_shape(self):
        services = _make_services({
            "switchboard": {"url": "http://localhost:20401", "required": True},
        })
        with patch("workstation_cli.status.check_all_health",
                   side_effect=_mock_health({"switchboard"})):
            result = aggregate_status(services)

        assert result["platform"] == "workstation"
        assert "status" in result
        assert "timestamp" in result
        assert "services" in result

        svc_entry = result["services"]["switchboard"]
        assert "status" in svc_entry
        assert "base_url" in svc_entry
        assert "health_url" in svc_entry

    def test_service_status_values(self):
        services = _make_services({
            "switchboard": {"url": "http://localhost:20401", "required": True},
            "ninerouter":  {"url": "http://localhost:20128", "required": True},
        })
        with patch("workstation_cli.status.check_all_health",
                   side_effect=_mock_health({"switchboard"})):
            result = aggregate_status(services)

        assert result["services"]["switchboard"]["status"] == "healthy"
        assert result["services"]["ninerouter"]["status"] == "unhealthy"

    def test_timestamp_format(self):
        services = _make_services({
            "switchboard": {"url": "http://localhost:20401"},
        })
        with patch("workstation_cli.status.check_all_health",
                   side_effect=_mock_health({"switchboard"})):
            result = aggregate_status(services)
        ts = result["timestamp"]
        assert ts.endswith("Z")
        assert "T" in ts


# ── Tests: missing config behaviour ──────────────────────────────────────────

class TestMissingConfig:
    def test_load_config_missing_endpoints_raises_file_not_found(self, tmp_path: Path):
        d = tmp_path / "ws"
        d.mkdir()
        with pytest.raises(FileNotFoundError):
            load_config(d)

    def test_load_endpoints_missing_raises_file_not_found(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            load_endpoints(tmp_path / "no_such_file.yaml")

    def test_load_endpoints_empty_services(self, tmp_path: Path):
        p = _write(tmp_path / "endpoints.yaml", "services: {}\n")
        result = load_endpoints(p)
        assert result == {}
