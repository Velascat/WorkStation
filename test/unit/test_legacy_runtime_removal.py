from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_base_compose_has_no_ninerouter_service() -> None:
    compose = (REPO_ROOT / "compose" / "docker-compose.yml").read_text(encoding="utf-8")
    assert "ninerouter:" not in compose
    assert "PORT_9ROUTER" not in compose


def test_startup_flow_no_longer_instructs_9router_setup() -> None:
    startup = (REPO_ROOT / "docs" / "startup-flow.md").read_text(encoding="utf-8")
    assert "config/9router" not in startup
    assert "9router" not in startup
