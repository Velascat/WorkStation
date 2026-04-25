# Archon Adapter Architecture

This document describes the Phase 8 Archon backend adapter — the second execution backend in the contract-owned platform architecture, following the kodo reference pattern.

---

## Why Archon is optional and bounded

Archon is a workflow-oriented execution engine. It differs from kodo in that it runs multi-step agentic workflows internally (plan → execute → validate) rather than a single subprocess invocation. This makes it powerful but also more opaque.

The adapter integrates Archon as one option within the existing backend selection mechanism — it does not replace or subsume kodo. Hard constraints for this phase:

- Archon is **not** the universal backend
- `aider_local` lane runs stay on kodo; Archon is not injected there
- Archon-native types (`ArchonWorkflowConfig`, `ArchonRunCapture`, `workflow_events`) live inside `backends/archon/` and do not cross into canonical contracts
- No Archon workflow semantics in `ExecutionRequest`, `ExecutionResult`, or `LaneDecision`

---

## Layer structure

```
ExecutionRequest  ──►  mapper.py         ──►  ArchonWorkflowConfig
                                                    │
                        invoke.py         ──►  ArchonAdapter.run()
                                                    │
                                          ──►  ArchonRunResult
                                                    │
                        invoke.py         ──►  ArchonRunCapture
                                                    │
                        normalize.py      ──►  ExecutionResult  (canonical)
```

Each layer has one job and one dependency direction: downstream toward canonical contracts.

---

## What the adapter owns

| Responsibility | Owner |
|----------------|-------|
| Mapping `ExecutionRequest` → `ArchonWorkflowConfig` | `mapper.py` |
| Validating that Archon can handle the request | `mapper.py` (`check_support`) |
| Invoking the Archon adapter and timing the run | `invoke.py` (`ArchonBackendInvoker`) |
| Capturing `workflow_events`, timing, artifacts | `invoke.py` → `ArchonRunCapture` |
| Classifying failures and building failure reasons | `errors.py` |
| Normalizing `ArchonRunCapture` → canonical `ExecutionResult` | `normalize.py` |
| Wiring everything together for callers | `adapter.py` (`ArchonBackendAdapter`) |

---

## Key types

### `ArchonWorkflowConfig` (dataclass)

Archon-native configuration passed to the adapter. Contains `workflow_type` which selects the agentic strategy (`goal`, `fix_pr`, `test`, `improve`). This is entirely internal to the Archon namespace.

### `ArchonRunResult` (dataclass)

Raw output from `ArchonAdapter.run()`. Contains `outcome`, `exit_code`, `output_text`, `error_text`, and `workflow_events`. The `workflow_events` field holds Archon's internal step trace — these are retained for observability but never copied into canonical `ExecutionResult`.

### `ArchonRunCapture` (dataclass)

Enriched capture produced by `ArchonBackendInvoker.invoke()`. Adds timing (`started_at`, `finished_at`, `duration_ms`), `timeout_hit` detection, and log-excerpt artifacts extracted from output. This is the primary unit retained by the observability layer for `BackendDetailRef` creation.

### `SupportCheck` (dataclass)

Result of `check_support()`. Indicates whether Archon can handle a given `ExecutionRequest`, with `unsupported_fields` populated when it cannot.

---

## The `ArchonAdapter` base class

`ArchonAdapter` is a plain class (not ABC) with a single `run()` method that raises `NotImplementedError`. This design choice matters:

- `MagicMock(spec=ArchonAdapter)` works without implementing abstract methods
- `StubArchonAdapter` can inject a fixed `ArchonRunResult` for tests
- Real subclasses (subprocess-based, HTTP-based) extend the base without ceremony

---

## `execute_and_capture()` — the extended API

`ArchonBackendAdapter` exposes two methods:

```python
def execute(self, request) -> ExecutionResult:
    """Standard canonical interface — used by OperationsCenter's execution boundary."""

def execute_and_capture(self, request) -> tuple[ExecutionResult, ArchonRunCapture | None]:
    """Extended API — used by callers who need the raw capture for BackendDetailRef."""
```

`execute()` delegates to `execute_and_capture()` and discards the capture. The capture is `None` when:

- The request is not supported (policy-blocked before invocation)
- A mapping error occurs before invocation

When the capture is returned, its `workflow_events` can be referenced via `BackendDetailRef` without being inlined into the canonical result.

---

## Failure classification

`errors.py` classifies failures in priority order:

| Signal | Category |
|--------|----------|
| `outcome == "timeout"` | `TIMEOUT` |
| `"[timeout:"` or `"deadline exceeded"` in output | `TIMEOUT` |
| `"no changes"` or `"nothing to commit"` in output | `NO_CHANGES` |
| `"merge conflict"` in output | `CONFLICT` |
| `"validation failed"` or `"checks failed"` in output | `VALIDATION_FAILED` |
| anything else | `BACKEND_ERROR` |

---

## Workspace path sentinel

`check_support()` treats `workspace_path` as missing if `str(workspace_path) in ("", ".")`. This catches the case where `Path("")` is passed (which Python normalizes to `Path(".")`). A real workspace is always an absolute path with content.

---

## Workflow type mapping

`ExecutionRequest` can carry an `execution_mode_hint` that maps to Archon's `workflow_type`:

| execution_mode_hint | Archon workflow_type |
|---------------------|----------------------|
| `goal`              | `goal`               |
| `fix_pr`            | `fix_pr`             |
| `test_campaign`     | `test`               |
| `improve_campaign`  | `improve`            |
| (none / unknown)    | `goal`               |

Callers can also pass `workflow_type` explicitly to `map_request()` or `ArchonBackendAdapter.__init__()`.

---

## What does NOT cross into canonical contracts

The following are Archon-internal and must never appear in `ExecutionRequest`, `ExecutionResult`, `LaneDecision`, or any canonical type:

- `workflow_events` — Archon's internal step trace
- `workflow_type` — Archon's execution strategy name
- `ArchonWorkflowConfig` — Archon-specific config shape
- `ArchonRunCapture` / `ArchonRunResult` — raw invocation output

The canonical `ExecutionResult` is the same shape regardless of which backend produced it.
