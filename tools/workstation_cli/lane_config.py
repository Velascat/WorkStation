# SPDX-License-Identifier: SSPL-1.0
# Copyright (C) 2026 Velascat
"""
lane_config.py — Configuration model for the aider_local execution lane.

Defines the data types and YAML loader for WorkStation's local lane configuration.
The config covers: which lane is enabled, which local model services back it,
health check settings, and optional runtime paths.

Config file location (copy-to-activate pattern):
    config/workstation/local_lane.yaml
    (template: config/workstation/local_lane.example.yaml)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class HealthCheckConfig:
    """Settings that control how the lane manager polls model service health."""

    poll_interval_seconds: int = 30
    startup_timeout_seconds: int = 60
    consecutive_failures_before_unhealthy: int = 2


@dataclass
class TinyModelServiceConfig:
    """
    Configuration for a single local model service.

    A lane can have multiple model services (e.g. primary and secondary).
    Each one has its own endpoint. start_command / stop_command are optional:
    if absent, the manager assumes the service is already running and only
    checks reachability.
    """

    name: str
    model_id: str
    endpoint: str
    health_path: str = "/api/tags"
    start_command: Optional[str] = None
    stop_command: Optional[str] = None
    connect_timeout: float = 5.0
    read_timeout: float = 30.0

    @property
    def health_url(self) -> str:
        return self.endpoint.rstrip("/") + "/" + self.health_path.lstrip("/")

    @property
    def managed(self) -> bool:
        """True when the manager should start/stop this service."""
        return self.start_command is not None


@dataclass
class RuntimePathsConfig:
    """Optional local filesystem paths for model data and runtime files."""

    model_data_dir: str = "~/.workstation/models"
    logs_dir: str = "~/.workstation/logs/aider_local"
    pid_file: str = "~/.workstation/run/aider_local.pid"


@dataclass
class LocalLaneConfig:
    """
    Complete configuration for the aider_local execution lane.

    Owns: lane identity, list of backing model services, health check
    settings, and optional runtime paths.

    Does not own: routing policy, task selection, or SwitchBoard config.
    """

    lane_name: str = "aider_local"
    enabled: bool = True
    task_classes: List[str] = field(
        default_factory=lambda: ["lint_fix", "simple_edit", "documentation"]
    )
    models: List[TinyModelServiceConfig] = field(default_factory=list)
    health_check: HealthCheckConfig = field(default_factory=HealthCheckConfig)
    runtime_paths: RuntimePathsConfig = field(default_factory=RuntimePathsConfig)


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

def _require_yaml() -> None:
    if yaml is None:  # pragma: no cover
        raise ImportError("PyYAML is required. Install it with: pip install pyyaml")


def load_local_lane_config(path: Path) -> LocalLaneConfig:
    """
    Parse a local_lane.yaml file and return a LocalLaneConfig.

    Expected structure (see config/workstation/local_lane.example.yaml):

        lane:
          name: aider_local
          enabled: true
          task_classes:
            - lint_fix
            - simple_edit

        models:
          - name: primary
            model_id: qwen2.5-coder:1.5b
            endpoint: "http://localhost:11434"
            health_path: "/api/tags"
            connect_timeout: 5
            read_timeout: 30

        health_check:
          poll_interval_seconds: 30
          startup_timeout_seconds: 60
          consecutive_failures_before_unhealthy: 2

        runtime_paths:
          model_data_dir: "~/.workstation/models"
          logs_dir: "~/.workstation/logs/aider_local"
          pid_file: "~/.workstation/run/aider_local.pid"

    Raises:
        FileNotFoundError: if the path does not exist.
        ValueError: if required fields are missing or malformed.
    """
    _require_yaml()

    if not path.exists():
        raise FileNotFoundError(
            f"Local lane config not found: {path}\n"
            "Copy config/workstation/local_lane.example.yaml to local_lane.yaml first."
        )

    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    if not isinstance(data, dict):
        raise ValueError(f"Invalid local lane config at {path}: expected a YAML mapping.")

    # Lane section
    lane_section = data.get("lane", {})
    if not isinstance(lane_section, dict):
        raise ValueError(f"'lane' section in {path} must be a mapping.")

    lane_name = lane_section.get("name", "aider_local")
    enabled = bool(lane_section.get("enabled", True))
    task_classes = lane_section.get("task_classes", ["lint_fix", "simple_edit", "documentation"])
    if not isinstance(task_classes, list):
        raise ValueError(f"'lane.task_classes' in {path} must be a list.")

    # Models section
    raw_models = data.get("models", [])
    if not isinstance(raw_models, list):
        raise ValueError(f"'models' in {path} must be a list.")

    models: List[TinyModelServiceConfig] = []
    for i, m in enumerate(raw_models):
        if not isinstance(m, dict):
            raise ValueError(f"Model entry {i} in {path} must be a mapping.")
        if "name" not in m:
            raise ValueError(f"Model entry {i} in {path} is missing 'name'.")
        if "model_id" not in m:
            raise ValueError(f"Model '{m['name']}' in {path} is missing 'model_id'.")
        if "endpoint" not in m:
            raise ValueError(f"Model '{m['name']}' in {path} is missing 'endpoint'.")
        models.append(
            TinyModelServiceConfig(
                name=m["name"],
                model_id=m["model_id"],
                endpoint=m["endpoint"],
                health_path=m.get("health_path", "/api/tags"),
                start_command=m.get("start_command") or None,
                stop_command=m.get("stop_command") or None,
                connect_timeout=float(m.get("connect_timeout", 5.0)),
                read_timeout=float(m.get("read_timeout", 30.0)),
            )
        )

    # Health check section
    hc_raw = data.get("health_check", {})
    if not isinstance(hc_raw, dict):
        raise ValueError(f"'health_check' in {path} must be a mapping.")
    health_check = HealthCheckConfig(
        poll_interval_seconds=int(hc_raw.get("poll_interval_seconds", 30)),
        startup_timeout_seconds=int(hc_raw.get("startup_timeout_seconds", 60)),
        consecutive_failures_before_unhealthy=int(
            hc_raw.get("consecutive_failures_before_unhealthy", 2)
        ),
    )

    # Runtime paths section
    rp_raw = data.get("runtime_paths", {})
    if not isinstance(rp_raw, dict):
        raise ValueError(f"'runtime_paths' in {path} must be a mapping.")
    runtime_paths = RuntimePathsConfig(
        model_data_dir=rp_raw.get("model_data_dir", "~/.workstation/models"),
        logs_dir=rp_raw.get("logs_dir", "~/.workstation/logs/aider_local"),
        pid_file=rp_raw.get("pid_file", "~/.workstation/run/aider_local.pid"),
    )

    return LocalLaneConfig(
        lane_name=lane_name,
        enabled=enabled,
        task_classes=list(task_classes),
        models=models,
        health_check=health_check,
        runtime_paths=runtime_paths,
    )


def default_local_lane_config() -> LocalLaneConfig:
    """Return a default LocalLaneConfig suitable for initial setup without a file."""
    return LocalLaneConfig(
        lane_name="aider_local",
        enabled=False,
        task_classes=["lint_fix", "simple_edit", "documentation"],
        models=[],
        health_check=HealthCheckConfig(),
        runtime_paths=RuntimePathsConfig(),
    )
