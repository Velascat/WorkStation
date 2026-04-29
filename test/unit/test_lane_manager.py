# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Velascat
"""
test_lane_manager.py — Unit tests for LocalLaneManager.

All tests mock the HTTP health check so no real services are required.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools"))

from workstation_cli.lane_config import (  # noqa: E402
    HealthCheckConfig,
    LocalLaneConfig,
    RuntimePathsConfig,
    TinyModelServiceConfig,
)
from workstation_cli.lane_manager import LocalLaneManager  # noqa: E402
from workstation_cli.lane_models import LaneState  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_model(name: str, endpoint: str, start_command=None) -> TinyModelServiceConfig:
    return TinyModelServiceConfig(
        name=name,
        model_id=f"model-{name}",
        endpoint=endpoint,
        health_path="/api/tags",
        start_command=start_command,
        connect_timeout=1.0,
        read_timeout=2.0,
    )


def _make_config(
    enabled: bool = True,
    models=None,
    startup_timeout: int = 1,
) -> LocalLaneConfig:
    if models is None:
        models = [_make_model("primary", "http://localhost:11434")]
    return LocalLaneConfig(
        lane_name="aider_local",
        enabled=enabled,
        task_classes=["lint_fix"],
        models=models,
        health_check=HealthCheckConfig(
            poll_interval_seconds=1,
            startup_timeout_seconds=startup_timeout,
            consecutive_failures_before_unhealthy=2,
        ),
        runtime_paths=RuntimePathsConfig(),
    )


def _reachable(url, connect_timeout, read_timeout):
    return True, 5.0, None


def _unreachable(url, connect_timeout, read_timeout):
    return False, 50.0, "Connection refused"


# ---------------------------------------------------------------------------
# Initial state
# ---------------------------------------------------------------------------

class TestInitialState:
    def test_disabled_config_yields_disabled_state(self):
        cfg = _make_config(enabled=False)
        mgr = LocalLaneManager(cfg)
        status = mgr.get_status()
        assert status.state == LaneState.DISABLED

    def test_enabled_config_yields_configured_state(self):
        cfg = _make_config(enabled=True)
        mgr = LocalLaneManager(cfg)
        # get_status before start() calls check_health — mock it
        with patch(
            "workstation_cli.lane_manager._http_get_ok",
            side_effect=_reachable,
        ):
            status = mgr.get_status()
        assert status.state == LaneState.READY

    def test_is_ready_false_when_model_unreachable(self):
        cfg = _make_config()
        mgr = LocalLaneManager(cfg)
        with patch("workstation_cli.lane_manager._http_get_ok", side_effect=_unreachable):
            assert mgr.is_ready() is False

    def test_is_ready_true_when_model_reachable(self):
        cfg = _make_config()
        mgr = LocalLaneManager(cfg)
        with patch("workstation_cli.lane_manager._http_get_ok", side_effect=_reachable):
            assert mgr.is_ready() is True


# ---------------------------------------------------------------------------
# check_health
# ---------------------------------------------------------------------------

class TestCheckHealth:
    def test_ready_when_all_models_reachable(self):
        cfg = _make_config(models=[
            _make_model("primary", "http://localhost:11434"),
            _make_model("secondary", "http://localhost:11435"),
        ])
        mgr = LocalLaneManager(cfg)
        with patch("workstation_cli.lane_manager._http_get_ok", side_effect=_reachable):
            status = mgr.check_health()
        assert status.state == LaneState.READY
        assert status.ready is True
        assert status.reachable_model_count() == 2

    def test_unhealthy_when_model_unreachable(self):
        cfg = _make_config()
        mgr = LocalLaneManager(cfg)
        with patch("workstation_cli.lane_manager._http_get_ok", side_effect=_unreachable):
            status = mgr.check_health()
        assert status.state == LaneState.UNHEALTHY
        assert status.ready is False

    def test_failure_reason_set_when_unreachable(self):
        cfg = _make_config()
        mgr = LocalLaneManager(cfg)
        with patch("workstation_cli.lane_manager._http_get_ok", side_effect=_unreachable):
            status = mgr.check_health()
        assert status.failure_reason is not None
        assert "primary" in status.failure_reason

    def test_unhealthy_when_no_models(self):
        cfg = _make_config(models=[])
        mgr = LocalLaneManager(cfg)
        status = mgr.check_health()
        assert status.state == LaneState.UNHEALTHY
        assert "No model services" in (status.failure_reason or "")

    def test_disabled_lane_returns_disabled_state(self):
        cfg = _make_config(enabled=False)
        mgr = LocalLaneManager(cfg)
        status = mgr.check_health()
        assert status.state == LaneState.DISABLED

    def test_model_results_populated(self):
        cfg = _make_config()
        mgr = LocalLaneManager(cfg)
        with patch("workstation_cli.lane_manager._http_get_ok", side_effect=_reachable):
            status = mgr.check_health()
        assert len(status.models) == 1
        assert status.models[0].model_name == "primary"
        assert status.models[0].reachable is True

    def test_partial_reachability(self):
        cfg = _make_config(models=[
            _make_model("primary", "http://localhost:11434"),
            _make_model("secondary", "http://localhost:11435"),
        ])
        mgr = LocalLaneManager(cfg)
        call_count = [0]

        def _alternating(url, connect_timeout, read_timeout):
            call_count[0] += 1
            if "11434" in url:
                return True, 5.0, None
            return False, 50.0, "refused"

        with patch("workstation_cli.lane_manager._http_get_ok", side_effect=_alternating):
            status = mgr.check_health()

        assert status.state == LaneState.UNHEALTHY
        assert status.reachable_model_count() == 1


# ---------------------------------------------------------------------------
# start()
# ---------------------------------------------------------------------------

class TestStart:
    def test_start_returns_ready_when_services_reachable(self):
        cfg = _make_config(startup_timeout=5)
        mgr = LocalLaneManager(cfg)
        with patch("workstation_cli.lane_manager._http_get_ok", side_effect=_reachable):
            status = mgr.start()
        assert status.state == LaneState.READY

    def test_start_disabled_lane_returns_disabled(self):
        cfg = _make_config(enabled=False)
        mgr = LocalLaneManager(cfg)
        status = mgr.start()
        assert status.state == LaneState.DISABLED

    def test_start_timeout_yields_unhealthy(self):
        cfg = _make_config(startup_timeout=1)
        mgr = LocalLaneManager(cfg)
        with patch("workstation_cli.lane_manager._http_get_ok", side_effect=_unreachable):
            status = mgr.start()
        assert status.state == LaneState.UNHEALTHY
        assert "Startup timeout" in (status.failure_reason or "")


# ---------------------------------------------------------------------------
# stop()
# ---------------------------------------------------------------------------

class TestStop:
    def test_stop_returns_stopped_state(self):
        cfg = _make_config()
        mgr = LocalLaneManager(cfg)
        status = mgr.stop()
        assert status.state == LaneState.STOPPED

    def test_stop_ready_lane(self):
        cfg = _make_config()
        mgr = LocalLaneManager(cfg)
        with patch("workstation_cli.lane_manager._http_get_ok", side_effect=_reachable):
            mgr.start()
        status = mgr.stop()
        assert status.state == LaneState.STOPPED


# ---------------------------------------------------------------------------
# get_capability and get_availability
# ---------------------------------------------------------------------------

class TestCapabilityAndAvailability:
    def test_capability_lane_name(self):
        cfg = _make_config()
        mgr = LocalLaneManager(cfg)
        cap = mgr.get_capability()
        assert cap.lane_name == "aider_local"

    def test_capability_local_only(self):
        cfg = _make_config()
        mgr = LocalLaneManager(cfg)
        cap = mgr.get_capability()
        assert cap.local_only is True
        assert cap.requires_external_auth is False

    def test_capability_model_count(self):
        cfg = _make_config(models=[
            _make_model("primary", "http://localhost:11434"),
            _make_model("secondary", "http://localhost:11435"),
        ])
        mgr = LocalLaneManager(cfg)
        cap = mgr.get_capability()
        assert cap.model_count == 2

    def test_availability_available_when_ready(self):
        cfg = _make_config()
        mgr = LocalLaneManager(cfg)
        with patch("workstation_cli.lane_manager._http_get_ok", side_effect=_reachable):
            av = mgr.get_availability()
        assert av.available is True
        assert av.current_state == LaneState.READY

    def test_availability_not_available_when_unreachable(self):
        cfg = _make_config()
        mgr = LocalLaneManager(cfg)
        with patch("workstation_cli.lane_manager._http_get_ok", side_effect=_unreachable):
            av = mgr.get_availability()
        assert av.available is False
        assert av.current_state == LaneState.UNHEALTHY

    def test_availability_has_capability(self):
        cfg = _make_config()
        mgr = LocalLaneManager(cfg)
        with patch("workstation_cli.lane_manager._http_get_ok", side_effect=_reachable):
            av = mgr.get_availability()
        assert av.capability is not None
        assert av.capability.lane_name == "aider_local"
