# SPDX-License-Identifier: SSPL-1.0
# Copyright (C) 2026 Velascat
"""
test_lane_models.py — Unit tests for lane runtime state models.

Tests cover LaneState transitions and helpers, LaneStatus summary output,
and LaneAvailability construction.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools"))

from workstation_cli.lane_models import (  # noqa: E402
    LaneAvailability,
    LaneCapability,
    LaneState,
    LaneStatus,
    ModelHealthResult,
)


# ---------------------------------------------------------------------------
# LaneState
# ---------------------------------------------------------------------------

class TestLaneState:
    def test_is_terminal_disabled(self):
        assert LaneState.DISABLED.is_terminal() is True

    def test_is_terminal_stopped(self):
        assert LaneState.STOPPED.is_terminal() is True

    def test_is_terminal_failed(self):
        assert LaneState.FAILED.is_terminal() is True

    def test_is_terminal_ready_false(self):
        assert LaneState.READY.is_terminal() is False

    def test_is_terminal_unhealthy_false(self):
        assert LaneState.UNHEALTHY.is_terminal() is False

    def test_is_operational_only_ready(self):
        assert LaneState.READY.is_operational() is True
        for state in LaneState:
            if state != LaneState.READY:
                assert state.is_operational() is False

    def test_all_states_have_string_value(self):
        expected = {"disabled", "configured", "starting", "ready", "unhealthy", "stopped", "failed"}
        actual = {s.value for s in LaneState}
        assert actual == expected


# ---------------------------------------------------------------------------
# ModelHealthResult
# ---------------------------------------------------------------------------

class TestModelHealthResult:
    def test_reachable(self):
        r = ModelHealthResult(
            model_name="primary",
            endpoint="http://localhost:11434",
            reachable=True,
            latency_ms=12.5,
        )
        assert r.reachable is True
        assert r.failure_reason is None

    def test_unreachable(self):
        r = ModelHealthResult(
            model_name="primary",
            endpoint="http://localhost:11434",
            reachable=False,
            failure_reason="Connection refused",
        )
        assert r.reachable is False
        assert r.failure_reason == "Connection refused"


# ---------------------------------------------------------------------------
# LaneStatus
# ---------------------------------------------------------------------------

class TestLaneStatus:
    def _make_status(self, state: LaneState, models=None) -> LaneStatus:
        return LaneStatus(
            lane_name="aider_local",
            state=state,
            ready=(state == LaneState.READY),
            models=models or [],
        )

    def test_ready_true_when_state_ready(self):
        s = self._make_status(LaneState.READY)
        assert s.ready is True

    def test_ready_false_when_unhealthy(self):
        s = self._make_status(LaneState.UNHEALTHY)
        assert s.ready is False

    def test_reachable_model_count_all_ok(self):
        models = [
            ModelHealthResult("primary", "http://localhost:11434", reachable=True),
            ModelHealthResult("secondary", "http://localhost:11435", reachable=True),
        ]
        s = self._make_status(LaneState.READY, models)
        assert s.reachable_model_count() == 2

    def test_reachable_model_count_partial(self):
        models = [
            ModelHealthResult("primary", "http://localhost:11434", reachable=True),
            ModelHealthResult("secondary", "http://localhost:11435", reachable=False),
        ]
        s = self._make_status(LaneState.UNHEALTHY, models)
        assert s.reachable_model_count() == 1

    def test_reachable_model_count_none(self):
        s = self._make_status(LaneState.UNHEALTHY)
        assert s.reachable_model_count() == 0

    def test_summary_line_ready(self):
        models = [ModelHealthResult("primary", "http://localhost:11434", reachable=True)]
        s = self._make_status(LaneState.READY, models)
        line = s.summary_line()
        assert "READY" in line
        assert "aider_local" in line
        assert "1/1" in line

    def test_summary_line_includes_failure_reason(self):
        s = LaneStatus(
            lane_name="aider_local",
            state=LaneState.UNHEALTHY,
            ready=False,
            failure_reason="primary unreachable",
        )
        line = s.summary_line()
        assert "primary unreachable" in line

    def test_summary_line_no_models(self):
        s = self._make_status(LaneState.CONFIGURED)
        line = s.summary_line()
        assert "no models configured" in line

    def test_timestamp_is_set(self):
        s = self._make_status(LaneState.READY)
        assert s.timestamp.endswith("Z")
        assert "T" in s.timestamp


# ---------------------------------------------------------------------------
# LaneCapability
# ---------------------------------------------------------------------------

class TestLaneCapability:
    def test_local_only_default(self):
        cap = LaneCapability(
            lane_name="aider_local",
            supported_task_classes=["lint_fix"],
            model_count=1,
        )
        assert cap.local_only is True
        assert cap.requires_external_auth is False

    def test_supported_task_classes(self):
        cap = LaneCapability(
            lane_name="aider_local",
            supported_task_classes=["lint_fix", "simple_edit"],
            model_count=2,
        )
        assert "lint_fix" in cap.supported_task_classes
        assert "simple_edit" in cap.supported_task_classes


# ---------------------------------------------------------------------------
# LaneAvailability
# ---------------------------------------------------------------------------

class TestLaneAvailability:
    def test_available_when_ready(self):
        av = LaneAvailability(
            lane_name="aider_local",
            available=True,
            current_state=LaneState.READY,
        )
        assert av.available is True

    def test_unavailable_with_reason(self):
        av = LaneAvailability(
            lane_name="aider_local",
            available=False,
            current_state=LaneState.UNHEALTHY,
            reason="primary model unreachable",
        )
        assert av.available is False
        assert av.reason == "primary model unreachable"

    def test_timestamp_is_set(self):
        av = LaneAvailability(lane_name="aider_local", available=False)
        assert av.checked_at.endswith("Z")
