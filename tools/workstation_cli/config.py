"""
config.py — Unified configuration loader for workstation_cli.

Loads endpoint and service configuration from YAML files under
config/workstation/:

  endpoints.yaml   — service URLs, health paths, timeouts
  services.yaml    — required/optional flags per service
  ports.yaml       — canonical port assignments

All three files follow a copy-to-activate pattern: operators copy the
.example.* variants and customise them. This module reads the live files
and merges the information into ServiceConfig objects that the rest of
workstation_cli consumes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

try:
    import yaml  # PyYAML
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ServiceConfig:
    """Full configuration for a single WorkStation service."""

    name: str
    url: str
    health_path: str = "/health"
    description: str = ""
    required: bool = True
    connect_timeout: float = 3.0
    read_timeout: float = 10.0

    @property
    def health_url(self) -> str:
        """Full URL to the health endpoint."""
        return self.url.rstrip("/") + "/" + self.health_path.lstrip("/")

    @property
    def base_url(self) -> str:
        """Alias for url — used in status output."""
        return self.url


@dataclass
class WorkstationConfig:
    """Aggregated configuration for the full WorkStation stack."""

    services: Dict[str, ServiceConfig] = field(default_factory=dict)
    ports: Dict[str, int] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _require_yaml() -> None:
    if yaml is None:
        raise ImportError(
            "PyYAML is required. Install it with: pip install pyyaml"
        )


def _load_yaml(path: Path) -> dict:
    """Load and parse a YAML file; raise FileNotFoundError if missing."""
    _require_yaml()
    if not path.exists():
        raise FileNotFoundError(
            f"Config file not found: {path}\n"
            f"Copy {path.parent / (path.stem + '.example' + path.suffix)} "
            f"to {path.name} first."
        )
    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"Invalid config at {path}: expected a YAML mapping.")
    return data


# ---------------------------------------------------------------------------
# Public loaders
# ---------------------------------------------------------------------------

def load_endpoints(path: Path) -> Dict[str, ServiceConfig]:
    """
    Parse an endpoints.yaml file.

    Expected structure (see config/workstation/endpoints.example.yaml):

        version: "1"
        services:
          switchboard:
            url: "http://localhost:20401"
            health_path: "/health"
            description: "SwitchBoard API gateway"
        timeouts:
          connect: 3
          read: 10

    Returns a dict of {service_name: ServiceConfig}.
    """
    data = _load_yaml(path)

    timeouts = data.get("timeouts", {})
    connect_timeout = float(timeouts.get("connect", 3))
    read_timeout = float(timeouts.get("read", 10))

    raw_services = data.get("services", {})
    if not isinstance(raw_services, dict):
        raise ValueError(f"'services' in {path} must be a mapping.")

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


def load_services_meta(path: Path) -> Dict[str, dict]:
    """
    Parse a services.yaml file that declares required/optional flags.

    Expected structure (see config/workstation/services.example.yaml):

        services:
          - name: switchboard
            required: true
          - name: status
            required: false

    Returns a dict of {service_name: {"required": bool}}.
    """
    data = _load_yaml(path)

    raw = data.get("services", [])
    if not isinstance(raw, list):
        raise ValueError(f"'services' in {path} must be a list.")

    meta: Dict[str, dict] = {}
    for entry in raw:
        if not isinstance(entry, dict) or "name" not in entry:
            raise ValueError(f"Each entry in {path} must be a mapping with a 'name' key.")
        name = entry["name"]
        meta[name] = {"required": bool(entry.get("required", True))}

    return meta


def load_ports(path: Path) -> Dict[str, int]:
    """
    Parse a ports.yaml file.

    Expected structure (see config/workstation/ports.example.yaml):

        ports:
          switchboard: 20401
          status: 20400

    Returns a dict of {service_name: port}.
    """
    data = _load_yaml(path)

    raw = data.get("ports", {})
    if not isinstance(raw, dict):
        raise ValueError(f"'ports' in {path} must be a mapping.")

    return {name: int(port) for name, port in raw.items()}


def load_config(config_dir: Path) -> WorkstationConfig:
    """
    Load all workstation configuration from *config_dir*.

    Reads endpoints.yaml, services.yaml (optional), and ports.yaml (optional),
    and merges them into a WorkstationConfig.

    Only endpoints.yaml is required; if services.yaml or ports.yaml are absent
    the function uses defaults (all services required, ports from endpoint URLs).

    Args:
        config_dir: Path to the config/workstation/ directory.

    Returns:
        WorkstationConfig with merged service and port data.
    """
    endpoints_file = config_dir / "endpoints.yaml"
    services_file = config_dir / "services.yaml"
    ports_file = config_dir / "ports.yaml"

    # Endpoints are required.
    services = load_endpoints(endpoints_file)

    # Merge required flags from services.yaml if it exists.
    if services_file.exists():
        meta = load_services_meta(services_file)
        for name, svc in services.items():
            if name in meta:
                svc.required = meta[name]["required"]

    # Load port map if available.
    ports: Dict[str, int] = {}
    if ports_file.exists():
        ports = load_ports(ports_file)

    return WorkstationConfig(services=services, ports=ports)
