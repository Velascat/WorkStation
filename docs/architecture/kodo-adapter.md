# kodo Adapter Architecture

This document describes the Phase 5 kodo backend adapter — the first real
execution backend in the contract-owned platform architecture.

---

## Why kodo is the first backend

kodo is the best first integration target because it:

- supports headless/programmatic execution via subprocess
- has a clean direct-run posture (not workflow-heavy)
- returns structured outcome signals via exit code + output
- has an existing subprocess wrapper (`KodoAdapter`) inside OperationsCenter that
  the new canonical adapter can delegate to

This phase establishes the adapter pattern. Later backends (Archon, OpenClaw)
will follow the same structure.

---

## What the adapter owns

| Responsibility | Owner |
|----------------|-------|
| Mapping `ExecutionRequest` → kodo-compatible input | kodo adapter |
| Writing the goal file into the workspace | kodo adapter |
| Invoking the kodo subprocess | kodo adapter |
| Capturing stdout, stderr, timing | kodo adapter |
| Normalizing outputs → `ExecutionResult` | kodo adapter |
| kodo-specific error categorization | kodo adapter |

## What the adapter does not own

- Routing policy — that is SwitchBoard's job
- Task proposal generation — that is OperationsCenter domain logic
- Local model hosting — that is WorkStation's job
- Cross-backend orchestration — that is Archon's job
- Canonical contract definition — that is `operations_center.contracts`

---

## Adapter flow

```
ExecutionRequest
  │
  ▼
check_support()          ← is this request kodo-compatible?
  │ supported
  ▼
map_request()            ← ExecutionRequest → KodoPreparedRun
  │
  ▼
KodoBackendInvoker.invoke()
  ├── write_goal_file()  ← writes .kodo_goal.md into workspace
  ├── KodoAdapter.run()  ← subprocess invocation (existing layer)
  └── extract_artifacts() ← log excerpt capture
  │
  ▼
KodoRunCapture           ← raw outputs: exit_code, stdout, stderr, timing
  │
  ▼
normalize()              ← KodoRunCapture → ExecutionResult
  │
  ▼
ExecutionResult          ← canonical, JSON-serialisable, frozen
```

---

## Module layout

```
src/operations_center/backends/kodo/
  __init__.py    — public API: KodoBackendAdapter, SupportCheck
  adapter.py     — KodoBackendAdapter (entry point)
  mapper.py      — check_support(), map_request()
  invoke.py      — KodoBackendInvoker
  normalize.py   — normalize()
  models.py      — KodoPreparedRun, KodoRunCapture, KodoArtifactCapture,
                    KodoFailureInfo, SupportCheck
  errors.py      — categorize_failure(), build_failure_reason()
```

All kodo-specific types are quarantined inside this namespace. They do not
appear in OperationsCenter domain code, SwitchBoard, or WorkStation.

---

## Usage

```python
from operations_center.backends.kodo import KodoBackendAdapter
from operations_center.config.settings import KodoSettings

adapter = KodoBackendAdapter.from_settings(
    settings=KodoSettings(),
    switchboard_url="http://sb:20401",
    kodo_mode="goal",
)

# Optional: check suitability before executing
check = adapter.supports(request)
if not check.supported:
    print(f"Not supported: {check.reason}")

# Execute
result = adapter.execute(request)   # ExecutionRequest → ExecutionResult
```

---

## Request mapping

`map_request()` translates a canonical `ExecutionRequest` into a `KodoPreparedRun`:

| ExecutionRequest field | KodoPreparedRun field |
|------------------------|----------------------|
| `run_id` | `run_id` |
| `goal_text` | `goal_text` |
| `constraints_text` | `constraints_text` |
| `workspace_path` | `repo_path` |
| `task_branch` | `task_branch` |
| `goal_file_path` (or derived) | `goal_file_path` |
| `validation_commands` | `validation_commands` |
| `timeout_seconds` | `timeout_seconds` |
| (caller-supplied) | `kodo_mode` (goal / test / improve) |

If `goal_file_path` is not set in the request, the mapper derives it as
`workspace_path / ".kodo_goal.md"`.

---

## Invocation boundary

`KodoBackendInvoker` isolates subprocess details:

- writes the goal file before running
- injects `OPENAI_API_BASE` into subprocess env when `switchboard_url` is set
  (so kodo worker agents route through SwitchBoard)
- delegates to the existing `KodoAdapter._run_subprocess()` with process-group
  management and SIGTERM handling
- measures wall-clock duration
- cleans up the goal file after run (even on failure)
- classifies `timeout_hit`, `rate_limited`, `quota_exhausted` from output

---

## Result normalization

`normalize()` maps `KodoRunCapture` → `ExecutionResult`:

**Success:** exit code 0 → `status=SUCCESS`, `success=True`

**Failure:** non-zero exit → `status=FAILED`, `success=False`, `failure_category` set

**Timeout:** `timeout_hit=True` → `status=TIMEOUT`

**Changed files:** discovered by running `git diff --name-status HEAD` in the
workspace. Returns an empty list when git is unavailable or the workspace is
not a git repo — this is normal, not an error.

**Validation:** the normalizer accepts `validation_ran`, `validation_passed`,
and `validation_excerpt` from the caller (e.g. OperationsCenter's execution
boundary when it ran validation commands separately). When not provided,
`ValidationSummary(status=SKIPPED)` is used.

**Branch push:** always `False` in the adapter. Pushing is a lane-runner concern.

---

## Error categories

The adapter distinguishes these failure categories:

| Category | When |
|----------|------|
| `unsupported_request` | Request failed adapter support check (missing fields / incompatible request) |
| `backend_error` | Generic kodo failure; also quota/rate-limit errors |
| `timeout` | `[timeout:` in stderr |
| `no_changes` | "nothing to commit" in output |
| `conflict` | "merge conflict" in output |
| `unknown` | exit 0 but flagged as failure by normalizer |

---

## Partial-richness expectations

The adapter does not fabricate output it cannot observe:

- **Changed files:** omitted when `git diff` fails or workspace is unavailable.
  Callers must not assume this list is always populated.
- **Validation summary:** skipped unless the caller provides it.
- **Pull request URL:** never set by the adapter; set by OperationsCenter's execution boundary or a higher workflow layer.
- **Branch push status:** never set by the adapter; set by OperationsCenter's execution boundary or a higher workflow layer.

---

## Relationship to existing KodoAdapter

`KodoBackendAdapter` (Phase 5) wraps `KodoAdapter` (existing subprocess layer).

```
KodoBackendAdapter     ← canonical boundary (Phase 5)
  └── KodoBackendInvoker
        └── KodoAdapter ← subprocess layer (existing)
```

`KodoAdapter` continues to own: subprocess launch, process-group management,
SIGTERM handling, timeout enforcement, codex-quota fallback to Claude.

`KodoBackendAdapter` adds: canonical request/result mapping, support checks,
error categorization, and the clean `ExecutionRequest → ExecutionResult` boundary.

---

## What this phase intentionally leaves unimplemented

- **Validation command execution** — the adapter reports validation results
  provided by the caller but does not run validation commands itself. That
  is a lane-runner concern.
- **Branch push / PR opening** — lane-runner concern.
- **SwitchBoard availability query for kodo mode** — future phase.
- **Archon and OpenClaw adapters** — Phase 6+.
- **Multi-backend fallback** — future phase.
