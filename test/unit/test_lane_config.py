# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Velascat
"""
test_lane_config.py — Unit tests for local lane configuration parsing.

Tests cover: happy path loading, field defaults, validation errors, and
the shipped example file.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

import sys
_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools"))

from workstation_cli.lane_config import (  # noqa: E402
    HealthCheckConfig,
    LocalLaneConfig,
    RuntimePathsConfig,
    TinyModelServiceConfig,
    default_local_lane_config,
    load_local_lane_config,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write(path: Path, text: str) -> Path:
    path.write_text(textwrap.dedent(text), encoding="utf-8")
    return path


def _minimal_yaml(tmp_path: Path) -> Path:
    return _write(tmp_path / "local_lane.yaml", """\
        lane:
          name: aider_local
          enabled: true
          task_classes:
            - lint_fix

        models:
          - name: primary
            model_id: qwen2.5-coder:1.5b
            endpoint: "http://localhost:11434"
    """)


def _full_yaml(tmp_path: Path) -> Path:
    return _write(tmp_path / "local_lane.yaml", """\
        lane:
          name: aider_local
          enabled: true
          task_classes:
            - lint_fix
            - simple_edit
            - documentation

        models:
          - name: primary
            model_id: qwen2.5-coder:1.5b
            endpoint: "http://localhost:11434"
            health_path: "/api/tags"
            connect_timeout: 5
            read_timeout: 30
          - name: secondary
            model_id: deepseek-coder:1.3b
            endpoint: "http://localhost:11435"
            health_path: "/api/tags"
            connect_timeout: 3
            read_timeout: 20

        health_check:
          poll_interval_seconds: 15
          startup_timeout_seconds: 45
          consecutive_failures_before_unhealthy: 3

        runtime_paths:
          model_data_dir: "/data/models"
          logs_dir: "/var/log/aider_local"
          pid_file: "/var/run/aider_local.pid"
    """)


# ---------------------------------------------------------------------------
# Happy path: minimal config
# ---------------------------------------------------------------------------

class TestLoadMinimalConfig:
    def test_returns_local_lane_config(self, tmp_path: Path):
        p = _minimal_yaml(tmp_path)
        cfg = load_local_lane_config(p)
        assert isinstance(cfg, LocalLaneConfig)

    def test_lane_name(self, tmp_path: Path):
        p = _minimal_yaml(tmp_path)
        cfg = load_local_lane_config(p)
        assert cfg.lane_name == "aider_local"

    def test_enabled(self, tmp_path: Path):
        p = _minimal_yaml(tmp_path)
        cfg = load_local_lane_config(p)
        assert cfg.enabled is True

    def test_task_classes(self, tmp_path: Path):
        p = _minimal_yaml(tmp_path)
        cfg = load_local_lane_config(p)
        assert cfg.task_classes == ["lint_fix"]

    def test_model_loaded(self, tmp_path: Path):
        p = _minimal_yaml(tmp_path)
        cfg = load_local_lane_config(p)
        assert len(cfg.models) == 1
        m = cfg.models[0]
        assert isinstance(m, TinyModelServiceConfig)
        assert m.name == "primary"
        assert m.model_id == "qwen2.5-coder:1.5b"
        assert m.endpoint == "http://localhost:11434"

    def test_model_defaults(self, tmp_path: Path):
        p = _minimal_yaml(tmp_path)
        cfg = load_local_lane_config(p)
        m = cfg.models[0]
        assert m.health_path == "/api/tags"
        assert m.start_command is None
        assert m.stop_command is None
        assert m.connect_timeout == 5.0
        assert m.read_timeout == 30.0

    def test_health_check_defaults(self, tmp_path: Path):
        p = _minimal_yaml(tmp_path)
        cfg = load_local_lane_config(p)
        assert isinstance(cfg.health_check, HealthCheckConfig)
        assert cfg.health_check.poll_interval_seconds == 30
        assert cfg.health_check.startup_timeout_seconds == 60
        assert cfg.health_check.consecutive_failures_before_unhealthy == 2

    def test_runtime_paths_defaults(self, tmp_path: Path):
        p = _minimal_yaml(tmp_path)
        cfg = load_local_lane_config(p)
        assert isinstance(cfg.runtime_paths, RuntimePathsConfig)
        assert "workstation" in cfg.runtime_paths.model_data_dir


# ---------------------------------------------------------------------------
# Happy path: full config
# ---------------------------------------------------------------------------

class TestLoadFullConfig:
    def test_two_models(self, tmp_path: Path):
        p = _full_yaml(tmp_path)
        cfg = load_local_lane_config(p)
        assert len(cfg.models) == 2

    def test_secondary_model(self, tmp_path: Path):
        p = _full_yaml(tmp_path)
        cfg = load_local_lane_config(p)
        secondary = next(m for m in cfg.models if m.name == "secondary")
        assert secondary.model_id == "deepseek-coder:1.3b"
        assert secondary.endpoint == "http://localhost:11435"
        assert secondary.connect_timeout == 3.0
        assert secondary.read_timeout == 20.0

    def test_health_check_overrides(self, tmp_path: Path):
        p = _full_yaml(tmp_path)
        cfg = load_local_lane_config(p)
        assert cfg.health_check.poll_interval_seconds == 15
        assert cfg.health_check.startup_timeout_seconds == 45
        assert cfg.health_check.consecutive_failures_before_unhealthy == 3

    def test_runtime_paths_override(self, tmp_path: Path):
        p = _full_yaml(tmp_path)
        cfg = load_local_lane_config(p)
        assert cfg.runtime_paths.model_data_dir == "/data/models"
        assert cfg.runtime_paths.logs_dir == "/var/log/aider_local"
        assert cfg.runtime_paths.pid_file == "/var/run/aider_local.pid"

    def test_task_classes(self, tmp_path: Path):
        p = _full_yaml(tmp_path)
        cfg = load_local_lane_config(p)
        assert set(cfg.task_classes) == {"lint_fix", "simple_edit", "documentation"}


# ---------------------------------------------------------------------------
# TinyModelServiceConfig properties
# ---------------------------------------------------------------------------

class TestTinyModelServiceConfig:
    def test_health_url(self):
        m = TinyModelServiceConfig(
            name="primary",
            model_id="qwen2.5-coder:1.5b",
            endpoint="http://localhost:11434",
            health_path="/api/tags",
        )
        assert m.health_url == "http://localhost:11434/api/tags"

    def test_health_url_strips_trailing_slash(self):
        m = TinyModelServiceConfig(
            name="primary",
            model_id="x",
            endpoint="http://localhost:11434/",
            health_path="/api/tags",
        )
        assert m.health_url == "http://localhost:11434/api/tags"

    def test_health_url_leading_slash_on_path(self):
        m = TinyModelServiceConfig(
            name="primary",
            model_id="x",
            endpoint="http://localhost:11434",
            health_path="api/tags",
        )
        assert m.health_url == "http://localhost:11434/api/tags"

    def test_managed_false_when_no_start_command(self):
        m = TinyModelServiceConfig(name="x", model_id="y", endpoint="http://localhost:1234")
        assert m.managed is False

    def test_managed_true_when_start_command_set(self):
        m = TinyModelServiceConfig(
            name="x", model_id="y", endpoint="http://localhost:1234",
            start_command="ollama serve",
        )
        assert m.managed is True


# ---------------------------------------------------------------------------
# Disabled lane
# ---------------------------------------------------------------------------

class TestDisabledLane:
    def test_enabled_false(self, tmp_path: Path):
        p = _write(tmp_path / "local_lane.yaml", """\
            lane:
              name: aider_local
              enabled: false
            models: []
        """)
        cfg = load_local_lane_config(p)
        assert cfg.enabled is False


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------

class TestValidationErrors:
    def test_missing_file_raises_file_not_found(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            load_local_lane_config(tmp_path / "does_not_exist.yaml")

    def test_non_mapping_raises_value_error(self, tmp_path: Path):
        p = tmp_path / "bad.yaml"
        p.write_text("- just a list\n")
        with pytest.raises(ValueError, match="expected a YAML mapping"):
            load_local_lane_config(p)

    def test_model_missing_name_raises(self, tmp_path: Path):
        p = _write(tmp_path / "local_lane.yaml", """\
            lane:
              name: aider_local
            models:
              - model_id: x
                endpoint: "http://localhost:11434"
        """)
        with pytest.raises(ValueError, match="missing 'name'"):
            load_local_lane_config(p)

    def test_model_missing_model_id_raises(self, tmp_path: Path):
        p = _write(tmp_path / "local_lane.yaml", """\
            lane:
              name: aider_local
            models:
              - name: primary
                endpoint: "http://localhost:11434"
        """)
        with pytest.raises(ValueError, match="missing 'model_id'"):
            load_local_lane_config(p)

    def test_model_missing_endpoint_raises(self, tmp_path: Path):
        p = _write(tmp_path / "local_lane.yaml", """\
            lane:
              name: aider_local
            models:
              - name: primary
                model_id: qwen2.5-coder:1.5b
        """)
        with pytest.raises(ValueError, match="missing 'endpoint'"):
            load_local_lane_config(p)


# ---------------------------------------------------------------------------
# default_local_lane_config
# ---------------------------------------------------------------------------

class TestDefaultLocalLaneConfig:
    def test_returns_local_lane_config(self):
        cfg = default_local_lane_config()
        assert isinstance(cfg, LocalLaneConfig)

    def test_disabled_by_default(self):
        cfg = default_local_lane_config()
        assert cfg.enabled is False

    def test_lane_name(self):
        cfg = default_local_lane_config()
        assert cfg.lane_name == "aider_local"

    def test_no_models(self):
        cfg = default_local_lane_config()
        assert cfg.models == []


# ---------------------------------------------------------------------------
# Example file smoke test
# ---------------------------------------------------------------------------

class TestExampleFileParses:
    def test_example_file_exists(self):
        example = _REPO_ROOT / "config" / "workstation" / "local_lane.example.yaml"
        assert example.exists(), f"Example file not found: {example}"

    def test_example_file_is_valid(self):
        example = _REPO_ROOT / "config" / "workstation" / "local_lane.example.yaml"
        cfg = load_local_lane_config(example)
        assert isinstance(cfg, LocalLaneConfig)

    def test_example_lane_name(self):
        example = _REPO_ROOT / "config" / "workstation" / "local_lane.example.yaml"
        cfg = load_local_lane_config(example)
        assert cfg.lane_name == "aider_local"

    def test_example_has_two_models(self):
        example = _REPO_ROOT / "config" / "workstation" / "local_lane.example.yaml"
        cfg = load_local_lane_config(example)
        assert len(cfg.models) == 2

    def test_example_model_endpoints(self):
        example = _REPO_ROOT / "config" / "workstation" / "local_lane.example.yaml"
        cfg = load_local_lane_config(example)
        endpoints = [m.endpoint for m in cfg.models]
        assert "http://localhost:11434" in endpoints
        assert "http://localhost:11435" in endpoints
