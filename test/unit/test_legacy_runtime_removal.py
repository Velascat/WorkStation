# SPDX-License-Identifier: SSPL-1.0
# Copyright (C) 2026 Velascat
from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_base_compose_has_no_ninerouter_service() -> None:
    compose = (REPO_ROOT / "compose" / "docker-compose.yml").read_text(encoding="utf-8")
    assert "switchboard:" in compose


def test_startup_flow_only_documents_current_stack_setup() -> None:
    startup = (REPO_ROOT / "docs" / "startup-flow.md").read_text(encoding="utf-8")
    assert "SwitchBoard" in startup
