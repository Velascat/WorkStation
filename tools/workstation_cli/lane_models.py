# SPDX-License-Identifier: SSPL-1.0
# Copyright (C) 2026 Velascat
"""
lane_models.py — Runtime state and capability models for the aider_local lane.

These types represent observable runtime state. They are intentionally
backend-neutral — they do not contain SwitchBoard routing logic or
OperationsCenter task proposal logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional


class LaneState(str, Enum):
    """Lifecycle states for the local execution lane."""

    DISABLED = "disabled"          # lane.enabled = false in config
    CONFIGURED = "configured"      # config loaded, services not yet started
    STARTING = "starting"          # start() called, waiting for readiness
    READY = "ready"                # all required services reachable
    UNHEALTHY = "unhealthy"        # services started but health checks failing
    STOPPED = "stopped"            # cleanly stopped
    FAILED = "failed"              # unrecoverable error; operator action needed

    def is_terminal(self) -> bool:
        return self in (LaneState.DISABLED, LaneState.STOPPED, LaneState.FAILED)

    def is_operational(self) -> bool:
        return self == LaneState.READY


@dataclass
class ModelHealthResult:
    """Health check result for a single model service."""

    model_name: str
    endpoint: str
    reachable: bool
    latency_ms: Optional[float] = None
    failure_reason: Optional[str] = None


@dataclass
class LaneStatus:
    """
    Point-in-time status snapshot for the aider_local lane.

    Produced by LocalLaneManager.get_status() and check_health().
    """

    lane_name: str
    state: LaneState
    ready: bool
    models: List[ModelHealthResult] = field(default_factory=list)
    failure_reason: Optional[str] = None
    timestamp: str = field(
        default_factory=lambda: datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    )

    def reachable_model_count(self) -> int:
        return sum(1 for m in self.models if m.reachable)

    def summary_line(self) -> str:
        """Single-line operator-readable summary."""
        reachable = self.reachable_model_count()
        total = len(self.models)
        state_str = self.state.value.upper()
        model_str = f"{reachable}/{total} models reachable" if total else "no models configured"
        if self.failure_reason:
            return f"[{state_str}]  {self.lane_name}  —  {model_str}  ({self.failure_reason})"
        return f"[{state_str}]  {self.lane_name}  —  {model_str}"


@dataclass
class LaneCapability:
    """
    Static description of what the aider_local lane can handle.

    Describes capability — not current availability.
    """

    lane_name: str
    supported_task_classes: List[str]
    model_count: int
    local_only: bool = True
    requires_external_auth: bool = False
    description: str = "Local Aider execution lane backed by tiny local models."


@dataclass
class LaneAvailability:
    """
    Current availability snapshot combining capability and live status.

    Consumers (e.g. SwitchBoard) can read this to decide whether the
    local lane is usable right now. WorkStation does not make the routing
    decision — it only reports availability.
    """

    lane_name: str
    available: bool
    capability: Optional[LaneCapability] = None
    current_state: LaneState = LaneState.CONFIGURED
    reason: Optional[str] = None
    checked_at: str = field(
        default_factory=lambda: datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    )
