# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Velascat
"""
services.py — ServiceConfig dataclass and YAML loader.

Parses config/workstation/endpoints.yaml into typed ServiceConfig objects
that the rest of workstation_cli consumes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict

try:
    import yaml  # PyYAML
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]


@dataclass
class ServiceConfig:
    """Holds the configuration for a single WorkStation service endpoint."""

    name: str
    url: str
    health_path: str = "/health"
    description: str = ""
    connect_timeout: float = 3.0
    read_timeout: float = 10.0

    @property
    def health_url(self) -> str:
        """Full URL to the /health endpoint."""
        return self.url.rstrip("/") + "/" + self.health_path.lstrip("/")


def load_services_from_yaml(path: Path) -> Dict[str, ServiceConfig]:
    """
    Parse an endpoints.yaml file and return a dict of {service_name: ServiceConfig}.

    Example YAML structure (see config/workstation/endpoints.example.yaml):

        version: "1"
        services:
          switchboard:
            url: "http://localhost:20401"
            health_path: "/health"
            description: "SwitchBoard API gateway"
        timeouts:
          connect: 3
          read: 10

    Returns:
        dict mapping service name -> ServiceConfig
    """
    if yaml is None:
        raise ImportError(
            "PyYAML is required to load service config. Install it with: pip install pyyaml"
        )

    if not path.exists():
        raise FileNotFoundError(
            f"Endpoints config not found: {path}\n"
            "Copy config/workstation/endpoints.example.yaml to endpoints.yaml first."
        )

    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    if not isinstance(data, dict):
        raise ValueError(f"Invalid endpoints config at {path}: expected a YAML mapping.")

    timeouts = data.get("timeouts", {})
    connect_timeout = float(timeouts.get("connect", 3))
    read_timeout = float(timeouts.get("read", 10))

    raw_services = data.get("services", {})
    if not isinstance(raw_services, dict):
        raise ValueError(f"'services' key in {path} must be a mapping.")

    services: Dict[str, ServiceConfig] = {}
    for name, svc in raw_services.items():
        if not isinstance(svc, dict):
            raise ValueError(f"Service '{name}' in {path} must be a mapping.")

        url = svc.get("url", "")
        if not url:
            raise ValueError(f"Service '{name}' in {path} is missing 'url'.")

        services[name] = ServiceConfig(
            name=name,
            url=url,
            health_path=svc.get("health_path", "/health"),
            description=svc.get("description", ""),
            connect_timeout=connect_timeout,
            read_timeout=read_timeout,
        )

    return services
