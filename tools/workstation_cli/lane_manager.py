# SPDX-License-Identifier: SSPL-1.0
# Copyright (C) 2026 Velascat
"""
lane_manager.py — Lifecycle manager for the aider_local execution lane.

Responsibilities:
  - start required local model services (if start_command is configured)
  - stop those services cleanly
  - health-check all configured model endpoints
  - report lane status and availability

This manager is intentionally local-first and single-machine. It does not
implement cross-backend routing, task proposal logic, or SwitchBoard policy.

Design notes:
  - If a model's start_command is None, the manager treats the service as
    externally managed (e.g. Ollama running as a system service) and only
    checks reachability.
  - Managed processes are tracked in memory. A stop() call terminates them.
  - Health checks use a plain HTTP GET to each model's health_url.
"""

from __future__ import annotations

import subprocess
import time
from typing import Dict, List, Optional

from .lane_config import LocalLaneConfig, TinyModelServiceConfig
from .lane_models import (
    LaneAvailability,
    LaneCapability,
    LaneState,
    LaneStatus,
    ModelHealthResult,
)


# ---------------------------------------------------------------------------
# HTTP check helper (stdlib-only, no required deps)
# ---------------------------------------------------------------------------

def _http_get_ok(url: str, connect_timeout: float, read_timeout: float) -> tuple[bool, Optional[float], Optional[str]]:
    """
    Perform a GET request to *url*.

    Returns: (reachable, latency_ms, failure_reason)
    """
    import time as _time

    start = _time.monotonic()
    try:
        try:
            import httpx
            with httpx.Client(
                timeout=httpx.Timeout(connect=connect_timeout, read=read_timeout, write=5.0, pool=5.0)
            ) as client:
                resp = client.get(url)
            latency_ms = round((_time.monotonic() - start) * 1000, 1)
            if resp.status_code == 200:
                return True, latency_ms, None
            return False, latency_ms, f"HTTP {resp.status_code}"
        except ImportError:
            import urllib.request
            import urllib.error
            req = urllib.request.Request(url, method="GET")
            try:
                with urllib.request.urlopen(req, timeout=read_timeout) as r:
                    latency_ms = round((_time.monotonic() - start) * 1000, 1)
                    return True, latency_ms, None
            except urllib.error.HTTPError as exc:
                latency_ms = round((_time.monotonic() - start) * 1000, 1)
                return False, latency_ms, f"HTTP {exc.code}"
    except Exception as exc:
        latency_ms = round((time.monotonic() - start) * 1000, 1)
        return False, latency_ms, f"{type(exc).__name__}: {exc}"


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------

class LocalLaneManager:
    """
    Manages the lifecycle and health of the aider_local lane.

    Usage:
        config = load_local_lane_config(path)
        manager = LocalLaneManager(config)

        manager.start()              # start managed model services
        status = manager.get_status()
        manager.stop()               # stop managed services

    The manager does not make routing decisions. It reports what is available.
    """

    def __init__(self, config: LocalLaneConfig) -> None:
        self._config = config
        self._processes: Dict[str, subprocess.Popen] = {}  # model name -> process
        self._state: LaneState = (
            LaneState.DISABLED if not config.enabled else LaneState.CONFIGURED
        )
        self._failure_reason: Optional[str] = None

    # ------------------------------------------------------------------
    # Public lifecycle API
    # ------------------------------------------------------------------

    def start(self) -> LaneStatus:
        """
        Start managed model services, then poll until ready or timeout.

        Services with no start_command are not started here — they are assumed
        to be externally managed.
        """
        if not self._config.enabled:
            self._state = LaneState.DISABLED
            return self.get_status()

        self._state = LaneState.STARTING
        self._failure_reason = None

        for model in self._config.models:
            if model.managed and model.name not in self._processes:
                self._start_model_process(model)

        # Poll for readiness up to startup_timeout_seconds
        deadline = time.monotonic() + self._config.health_check.startup_timeout_seconds
        while time.monotonic() < deadline:
            results = self._check_all_models()
            if self._all_reachable(results):
                self._state = LaneState.READY
                return self._build_status(results)
            time.sleep(2)

        # Timeout — mark unhealthy
        results = self._check_all_models()
        reachable = [r for r in results if r.reachable]
        total = len(results)
        self._failure_reason = (
            f"Startup timeout: {len(reachable)}/{total} model services reachable "
            f"after {self._config.health_check.startup_timeout_seconds}s"
        )
        self._state = LaneState.UNHEALTHY
        return self._build_status(results)

    def stop(self) -> LaneStatus:
        """Stop all managed model services."""
        for model in self._config.models:
            self._stop_model_process(model)

        self._processes.clear()
        self._state = LaneState.STOPPED
        return self.get_status()

    def get_status(self) -> LaneStatus:
        """Return current status. Checks health for all non-terminal states."""
        if self._state in (LaneState.DISABLED, LaneState.STOPPED):
            return self._build_status([])
        return self.check_health()

    def check_health(self) -> LaneStatus:
        """Perform a live health check on all configured model endpoints."""
        if not self._config.enabled:
            self._state = LaneState.DISABLED
            return self._build_status([])

        results = self._check_all_models()

        if not self._config.models:
            self._failure_reason = "No model services configured."
            self._state = LaneState.UNHEALTHY
        elif self._all_reachable(results):
            self._state = LaneState.READY
            self._failure_reason = None
        else:
            unreachable = [r.model_name for r in results if not r.reachable]
            self._failure_reason = f"Model services unreachable: {', '.join(unreachable)}"
            self._state = LaneState.UNHEALTHY

        return self._build_status(results)

    def is_ready(self) -> bool:
        """True only when all configured model services are reachable."""
        return self.check_health().state == LaneState.READY

    def get_capability(self) -> LaneCapability:
        return LaneCapability(
            lane_name=self._config.lane_name,
            supported_task_classes=list(self._config.task_classes),
            model_count=len(self._config.models),
            local_only=True,
            requires_external_auth=False,
        )

    def get_availability(self) -> LaneAvailability:
        status = self.check_health()
        return LaneAvailability(
            lane_name=self._config.lane_name,
            available=status.state == LaneState.READY,
            capability=self.get_capability(),
            current_state=status.state,
            reason=status.failure_reason,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _start_model_process(self, model: TinyModelServiceConfig) -> None:
        try:
            proc = subprocess.Popen(
                model.start_command,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._processes[model.name] = proc
        except Exception as exc:
            self._failure_reason = f"Failed to start '{model.name}': {exc}"
            self._state = LaneState.FAILED

    def _stop_model_process(self, model: TinyModelServiceConfig) -> None:
        if model.stop_command:
            try:
                subprocess.run(model.stop_command, shell=True, timeout=10)
            except Exception:
                pass

        proc = self._processes.get(model.name)
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

    def _check_all_models(self) -> List[ModelHealthResult]:
        results: List[ModelHealthResult] = []
        for model in self._config.models:
            reachable, latency_ms, failure = _http_get_ok(
                url=model.health_url,
                connect_timeout=model.connect_timeout,
                read_timeout=model.read_timeout,
            )
            results.append(
                ModelHealthResult(
                    model_name=model.name,
                    endpoint=model.endpoint,
                    reachable=reachable,
                    latency_ms=latency_ms,
                    failure_reason=failure,
                )
            )
        return results

    @staticmethod
    def _all_reachable(results: List[ModelHealthResult]) -> bool:
        return bool(results) and all(r.reachable for r in results)

    def _build_status(self, model_results: List[ModelHealthResult]) -> LaneStatus:
        return LaneStatus(
            lane_name=self._config.lane_name,
            state=self._state,
            ready=self._state == LaneState.READY,
            models=model_results,
            failure_reason=self._failure_reason,
        )
