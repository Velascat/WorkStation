# OpenClaw as the Optional Outer Shell

## Purpose

OpenClaw is an optional outer shell around the ControlPlane + SwitchBoard architecture. It provides an operator-facing command surface without modifying the internal contract-owned architecture. The system runs fully without OpenClaw active.

## Position in the Architecture

```
OpenClaw (outer shell — optional)
    └── OpenClawBridge        ← explicit crossing point
        └── OpenClawShellService
            ├── PlanningService       (routing + proposals)
            └── ExecutionObservabilityService  (record + trace)

ControlPlane core (unchanged, does not import from openclaw_shell/)
    ├── contracts/
    ├── planning/
    ├── routing/
    ├── backends/
    └── observability/
```

OpenClaw is "outer" in a strict sense: it imports inward, nothing inside the core architecture imports from `openclaw_shell/`.

## Integration Posture

OpenClaw adds three surface areas:

1. **Trigger** — an operator calls `bridge.trigger(context)` to plan a run. This maps `OperatorContext` → `PlanningContext` → `PlanningService.plan()` → `ProposalDecisionBundle` → `ShellRunHandle`. No execution happens here.

2. **Status** — derive `ShellStatusSummary` from a canonical `ExecutionResult` or `ExecutionRecord + ExecutionTrace`. Status truth originates from the internal observability layer; the shell only projects it.

3. **Inspection** — derive `ShellInspectionResult` from an `ExecutionRecord + ExecutionTrace`. A complete operator-readable view without exposing backend-native internals.

The shell never:
- Owns routing policy decisions
- Invokes backends directly
- Defines canonical contract types
- Stores execution records

## Optionality

The shell is controlled by a single environment variable:

```
OPENCLAW_SHELL_ENABLED=1   # shell active
OPENCLAW_SHELL_ENABLED=0   # shell inactive (default)
```

`OpenClawBridge.is_enabled()` reads this. The core architecture is unaware of this flag. Tests that exercise the core do not set it. Operator-facing code that gates on the shell checks it before constructing the bridge.

## Key Types

### Input

`OperatorContext` — plain Python dataclass. Uses plain strings rather than enum values to keep the shell interface ergonomic. The service maps this to `PlanningContext` before calling internal services.

### Outputs (all frozen Pydantic models)

| Type | Derived from | Purpose |
|------|-------------|---------|
| `ShellRunHandle` | `ProposalDecisionBundle` | Planned-but-not-executing run reference |
| `ShellStatusSummary` | `ExecutionRecord + ExecutionTrace` or `ExecutionResult` | Operator status view |
| `ShellInspectionResult` | `ExecutionRecord + ExecutionTrace` | Full operator inspection view |
| `ShellActionResult` | exception outcome | Generic shell action outcome |

All output types are frozen and JSON-serializable.

## Boundary Layers

### OpenClawBridge

The explicit crossing point between the outer shell and the internal architecture. This is the only class operator-facing code needs to interact with directly. It:

- Calls inward through `OpenClawShellService`
- Returns shell-facing types only
- Wraps arbitrary callables in `wrap_action()` to catch and surface exceptions without propagating them outward
- Exposes `is_enabled()` and factory methods (`default()`, `with_stub_routing()`)

### OpenClawShellService

The internal side of the boundary. Maps operator inputs to internal services and projects internal outputs to shell-facing types. Operator-facing code does not call this directly — it is internal to the shell layer.

## Status Derivation Direction

Status flows strictly inward-to-outward:

```
ExecutionResult / ExecutionRecord / ExecutionTrace
        ↓
    status.py (pure functions)
        ↓
    ShellStatusSummary / ShellInspectionResult
```

There is no path from shell types back into canonical contracts. The shell layer does not invent new execution truth.

Two status derivation paths exist:

- **Full path**: `summarize_result()` — uses `ExecutionObservabilityService` to build a full `ExecutionRecord + ExecutionTrace`, then derives the summary. Produces a `recorded_at` timestamp and full artifact/validation counts.
- **Lightweight path**: `summarize_result_lightweight()` — derives from the bare `ExecutionResult` without running the full observability pipeline. `recorded_at` is always `None`. Use when full observability is not available or not needed.

## Testing the Shell

Tests for the shell layer use stub routing (`OpenClawBridge.with_stub_routing()`) to avoid network calls. The shell's test suite does not mock internal contracts — it lets the real planning/observability stack run with the stub routing client in place.

The observability `conftest.py` fixtures (`make_result()`, `make_changed_file()`, etc.) are reused across the shell test suite to build `ExecutionResult` inputs consistently.

## What OpenClaw Does Not Own

| Concern | Owner |
|---------|-------|
| Routing policy rules | SwitchBoard |
| Fallback/escalation policy | SwitchBoard |
| Canonical contract definitions | ControlPlane contracts/ |
| Backend invocation | ControlPlane backends/ |
| Execution record storage | ControlPlane observability/ |
| Task proposal creation | ControlPlane planning/ |
| LaneDecision | SwitchBoard routing |

## File Map

```
src/control_plane/openclaw_shell/
    __init__.py        module version constant
    models.py          OperatorContext, ShellRunHandle, ShellStatusSummary,
                       ShellInspectionResult, ShellActionResult
    status.py          pure derivation functions (status_from_record, etc.)
    service.py         OpenClawShellService (internal boundary)
    bridge.py          OpenClawBridge (external crossing point)

tests/unit/openclaw_shell/
    test_models.py     model construction, defaults, frozen invariants
    test_status.py     pure status derivation function tests
    test_service.py    OpenClawShellService integration tests
    test_bridge.py     OpenClawBridge tests, is_enabled, wrap_action
```
