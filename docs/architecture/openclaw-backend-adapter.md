# OpenClaw Backend Adapter

## Purpose

The OpenClaw backend adapter makes OpenClaw available as an execution backend behind the canonical contract layer. It is a Phase 11 addition and is strictly separate from the Phase 10 optional outer-shell integration.

## Why This Is Separate from the Outer Shell

OpenClaw plays two distinct roles in the broader system:

| Role | Phase | Location | Purpose |
|------|-------|----------|---------|
| Backend adapter | Phase 11 | `backends/openclaw/` | Execution backend behind canonical contracts |
| Optional outer shell | Phase 10 | `openclaw_shell/` | Operator/runtime wrapper around the internal architecture |

These roles must not be collapsed. If they are:
- OpenClaw-centric execution truth contaminates the architecture
- Shell concerns leak into backend invocation
- Routing assumptions flow into the shell integration
- Backend event semantics infect canonical models

The backend adapter role is bounded: it accepts a canonical `ExecutionRequest`, invokes OpenClaw through an isolated boundary, and returns a canonical `ExecutionResult`. It does not own routing policy, proposal shaping, or the operator surface.

## Architecture Position

```
SwitchBoard selects openclaw lane/backend
          ↓
ControlPlane execution boundary builds ExecutionRequest
          ↓
OpenClawBackendAdapter (Phase 11)
  ├── check_support()      ← suitability check
  ├── map_request()        ← canonical → OpenClawPreparedRun
  ├── OpenClawBackendInvoker
  │     └── OpenClawRunner.run()  ← isolated invocation boundary
  ├── OpenClawRunCapture   ← raw events + changed_files_source
  └── normalize()          ← capture → ExecutionResult
          ↓
ExecutionResult (canonical)
          ↓
ExecutionObservabilityService
  └── changed_files_source visible to observability layer
```

## Flow Diagram

```
ExecutionRequest
  → mapper.check_support() → SupportCheck
  → mapper.map_request()   → OpenClawPreparedRun
  → invoker.invoke()       → OpenClawRunCapture
      (events, reported_changed_files, changed_files_source)
  → normalize()            → ExecutionResult
      (changed_files resolved: git_diff > event_stream > unknown)
```

## What the Backend Adapter Owns

- Mapping canonical `ExecutionRequest` to `OpenClawPreparedRun`
- Invoking OpenClaw through `OpenClawRunner` (isolated boundary)
- Capturing outputs, events, and backend-detail references
- Normalizing outputs into canonical `ExecutionResult`
- Representing changed-file evidence honestly

## What the Backend Adapter Does Not Own

- Canonical schema definitions
- Route selection (SwitchBoard owns that)
- Fallback/escalation policy
- Proposal shaping
- Local lane hosting
- The outer-shell/operator role (Phase 10)
- Normalized execution truth for the whole system

## File Map

```
src/control_plane/backends/openclaw/
  __init__.py     public surface: OpenClawBackendAdapter
  adapter.py      OpenClawBackendAdapter — canonical entry point
  mapper.py       check_support(), map_request() — pure functions
  invoke.py       OpenClawRunner, StubOpenClawRunner, OpenClawBackendInvoker
  normalize.py    normalize() — capture → ExecutionResult
  models.py       OpenClawPreparedRun, OpenClawRunCapture, SupportCheck, ...
  errors.py       categorize_failure(), build_failure_reason()
```

## Changed-File Evidence

This is the most important design distinction from other adapters.

OpenClaw may or may not provide a changed-files list in its event stream. The adapter must represent this honestly with three explicit states:

| Source | Value | Meaning |
|--------|-------|---------|
| `git_diff` | authoritative | git diff ran successfully on workspace |
| `event_stream` | inferred | OpenClaw reported files in its events; git diff unavailable |
| `unknown` | unavailable | no reliable source; `changed_files` is empty |

### Resolution order

1. Run `git diff --name-status HEAD` on `workspace_path` → source = `"git_diff"` (authoritative)
2. Fall back to `capture.reported_changed_files` from event stream → source = `"event_stream"` (inferred)
3. If neither is available → source = `"unknown"`, `changed_files = []`

The resolved source is stored in `capture.changed_files_source` so the observability layer can represent the evidence honestly in retained records.

**Inferred files are included in `ExecutionResult.changed_files`** when git diff is unavailable, but the `changed_files_source` makes the evidence quality transparent to downstream consumers.

**Unknown sources produce an empty `changed_files` list.** The system never pretends certainty it does not have.

### Why this matters

The observability layer's `ChangedFilesEvidence` model has `KNOWN / NONE / UNKNOWN / NOT_APPLICABLE` statuses. With `changed_files_source` surfaced in the capture, the observability layer can:
- Map `"git_diff"` + non-empty list → `KNOWN`
- Map `"event_stream"` + non-empty list → `KNOWN` (with lower confidence note)
- Map `"unknown"` or empty list → `UNKNOWN`

## Invocation Boundary

`OpenClawRunner` is the low-level interface:

```python
class OpenClawRunner:
    def run(self, prepared: OpenClawPreparedRun) -> OpenClawRunResult: ...
```

Subclass it to connect to a real OpenClaw service (subprocess, Python API, RPC). The invocation detail belongs here and must not escape into the adapter.

`StubOpenClawRunner` provides deterministic behavior for tests.

`OpenClawBackendInvoker` wraps `OpenClawRunner`, measures timing, detects timeout signals, extracts artifacts, and returns `OpenClawRunCapture`.

## Raw Event Handling

`OpenClawRunCapture.events` carries the raw OpenClaw event stream. This must NOT be inlined into canonical `ExecutionResult`. It is available to callers via `execute_and_capture()` for retention as `BackendDetailRef` entries through the observability layer.

```python
result, capture = adapter.execute_and_capture(request)
if capture:
    # capture.events → list[dict] for BackendDetailRef retention
    # capture.changed_files_source → "git_diff" | "event_stream" | "unknown"
```

## Error Categories

| Failure signal | FailureReasonCategory |
|---------------|----------------------|
| `outcome == "timeout"` or timeout signals in output | `TIMEOUT` |
| No changes / working tree clean | `NO_CHANGES` |
| Merge conflict signals | `CONFLICT` |
| Validation / test failure signals | `VALIDATION_FAILED` |
| Everything else | `BACKEND_ERROR` |
| Unsupported request (before invocation) | `POLICY_BLOCKED` |

## Suitability Checks

`check_support()` validates:
- `goal_text` must be non-empty
- `repo_key` must be non-empty
- `workspace_path` must not be empty sentinel (`Path("")` normalizes to `Path(".")`)

Unsupported requests return `POLICY_BLOCKED` immediately without invoking OpenClaw.

## Internal Model Quarantine

All OpenClaw-specific internal models are confined to `backends/openclaw/`:

| Model | Purpose |
|-------|---------|
| `OpenClawPreparedRun` | Mapped from `ExecutionRequest`; consumed by invoker |
| `OpenClawRunCapture` | Raw invocation output; consumed by normalizer |
| `OpenClawArtifactCapture` | Single captured artifact |
| `OpenClawEventDetailRef` | Reference to a raw event chunk (for BackendDetailRef) |
| `OpenClawFailureInfo` | Structured failure detail |
| `SupportCheck` | Support check result |

None of these replace canonical models.

## Testing

```
tests/unit/backends/openclaw/
  test_mapper.py     check_support(), map_request() — pure function tests
  test_errors.py     categorize_failure(), build_failure_reason()
  test_invoke.py     StubOpenClawRunner, OpenClawBackendInvoker
  test_normalize.py  normalize() — all three changed-file evidence paths
  test_adapter.py    OpenClawBackendAdapter end-to-end, separation assertions

tests/fixtures/backends/openclaw/
  run_result_success.json        successful run, git diff available
  run_result_inferred_files.json successful run, inferred from event stream
  run_result_failure.json        backend error
  run_result_timeout.json        timeout
```
