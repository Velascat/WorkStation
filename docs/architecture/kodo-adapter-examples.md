# kodo Adapter Examples

Concrete examples showing how canonical requests flow through the kodo adapter.

---

## Example 1 — Supported request, successful result

**ExecutionRequest (input):**

```json
{
  "run_id": "e5f6a7b8-c9d0-1234-ef01-234567890004",
  "proposal_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "decision_id": "c3d4e5f6-a7b8-9012-cdef-012345678902",
  "goal_text": "Fix all ruff lint errors in src/. Do not change logic.",
  "constraints_text": "Only modify files under src/. Do not touch tests/.",
  "repo_key": "api-service",
  "clone_url": "https://github.com/org/api-service.git",
  "base_branch": "main",
  "task_branch": "auto/lint-fix-TASK-1042-e5f6a7b8",
  "workspace_path": "/home/dev/workspaces/api-service-e5f6a7b8",
  "goal_file_path": null,
  "allowed_paths": ["src/**"],
  "max_changed_files": 20,
  "timeout_seconds": 300,
  "require_clean_validation": true,
  "validation_commands": ["ruff check src/"]
}
```

**SupportCheck:**
```python
SupportCheck(supported=True)
```

**KodoPreparedRun (internal, after mapping):**
```python
KodoPreparedRun(
    run_id="e5f6a7b8-...",
    goal_text="Fix all ruff lint errors in src/. Do not change logic.",
    constraints_text="Only modify files under src/. Do not touch tests/.",
    repo_path=Path("/home/dev/workspaces/api-service-e5f6a7b8"),
    task_branch="auto/lint-fix-TASK-1042-e5f6a7b8",
    goal_file_path=Path("/home/dev/workspaces/api-service-e5f6a7b8/.kodo_goal.md"),
    validation_commands=["ruff check src/"],
    timeout_seconds=300,
    kodo_mode="goal",
)
```

**ExecutionResult (output):**

```json
{
  "run_id": "e5f6a7b8-c9d0-1234-ef01-234567890004",
  "proposal_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "decision_id": "c3d4e5f6-a7b8-9012-cdef-012345678902",
  "status": "success",
  "success": true,
  "changed_files": [
    {"path": "src/main.py", "change_type": "modified", "lines_added": null, "lines_removed": null},
    {"path": "src/utils.py", "change_type": "modified", "lines_added": null, "lines_removed": null}
  ],
  "diff_stat_excerpt": "2 files changed",
  "validation": {
    "status": "skipped",
    "commands_run": 0,
    "commands_passed": 0,
    "commands_failed": 0,
    "failure_excerpt": null,
    "duration_ms": null
  },
  "branch_pushed": false,
  "branch_name": "auto/lint-fix-TASK-1042-e5f6a7b8",
  "pull_request_url": null,
  "failure_category": null,
  "failure_reason": null,
  "artifacts": [
    {
      "artifact_type": "log_excerpt",
      "label": "kodo run log",
      "content": "kodo: 2 files fixed\nkodo: done"
    }
  ]
}
```

**Note:** `validation` is `skipped` because the adapter does not run validation
commands — that is ControlPlane's execution boundary responsibility. That
boundary may pass
`validation_ran=True, validation_passed=True` to `normalize()` after running
validation separately.

---

## Example 2 — Supported request, failed result

**Request:** same as above but kodo exits 1 with an error.

**kodo output (captured internally):**
```
stdout: ""
stderr: "kodo: Claude Code error: 1 tool call failed\nkodo: exit 1"
exit_code: 1
```

**ExecutionResult (output):**

```json
{
  "run_id": "e5f6a7b8-...",
  "proposal_id": "a1b2c3d4-...",
  "decision_id": "c3d4e5f6-...",
  "status": "failed",
  "success": false,
  "changed_files": [],
  "diff_stat_excerpt": null,
  "validation": {"status": "skipped", "commands_run": 0, "commands_passed": 0, "commands_failed": 0, "failure_excerpt": null, "duration_ms": null},
  "branch_pushed": false,
  "branch_name": "auto/lint-fix-TASK-1042-e5f6a7b8",
  "pull_request_url": null,
  "failure_category": "backend_error",
  "failure_reason": "kodo exited 1: kodo: Claude Code error: 1 tool call failed kodo: exit 1",
  "artifacts": [
    {
      "artifact_type": "log_excerpt",
      "label": "kodo run log",
      "content": "kodo: Claude Code error: 1 tool call failed\nkodo: exit 1"
    }
  ]
}
```

---

## Example 3 — Timeout result

**kodo output:**
```
stderr: "[timeout: process group killed after 300s]"
exit_code: -1
```

**ExecutionResult (output):**

```json
{
  "status": "timeout",
  "success": false,
  "failure_category": "timeout",
  "failure_reason": "kodo exited -1: [timeout: process group killed after 300s]",
  "artifacts": [...]
}
```

---

## Example 4 — Unsupported request (graceful rejection)

**Request with empty goal_text:**

```json
{
  "goal_text": "",
  "repo_key": "api-service",
  ...
}
```

**SupportCheck:**
```python
SupportCheck(
    supported=False,
    reason="Required fields missing or empty: goal_text",
    unsupported_fields=["goal_text"]
)
```

**ExecutionResult (output) — returned immediately, kodo never invoked:**

```json
{
  "status": "failed",
  "success": false,
  "failure_category": "unsupported_request",
  "failure_reason": "Request not supported by kodo adapter: Required fields missing or empty: goal_text"
}
```

---

## Example 5 — Validation passed (execution boundary provides result)

ControlPlane's execution boundary can pass the
result into `normalize()`:

```python
result = normalize(
    capture=capture,
    proposal_id=request.proposal_id,
    decision_id=request.decision_id,
    branch_name=request.task_branch,
    workspace_path=Path(request.workspace_path),
    validation_ran=True,
    validation_passed=True,
    validation_duration_ms=840,
)
```

**ExecutionResult.validation:**
```json
{
  "status": "passed",
  "commands_run": 1,
  "commands_passed": 1,
  "commands_failed": 0,
  "failure_excerpt": null,
  "duration_ms": 840
}
```

---

## Using the adapter directly

```python
from control_plane.backends.kodo import KodoBackendAdapter
from control_plane.config.settings import KodoSettings
from control_plane.contracts.execution import ExecutionRequest
from pathlib import Path

adapter = KodoBackendAdapter.from_settings(
    settings=KodoSettings(timeout_seconds=600),
    switchboard_url="http://localhost:20401",
    kodo_mode="goal",
)

request = ExecutionRequest(
    proposal_id="prop-1",
    decision_id="dec-1",
    goal_text="Refactor the login module to use the new session API",
    repo_key="auth-service",
    clone_url="https://github.com/org/auth-service.git",
    base_branch="main",
    task_branch="auto/refactor-login-abc123",
    workspace_path=Path("/tmp/ws/auth-service"),
)

# Check first (optional)
check = adapter.supports(request)
assert check.supported

result = adapter.execute(request)
print(f"Status: {result.status.value}")
print(f"Success: {result.success}")
if not result.success:
    print(f"Failure: {result.failure_reason}")
```

---

## Adapter as reference pattern

`KodoBackendAdapter` is the template for future backend adapters. Each new
backend should follow the same structure:

```
backends/<name>/
  adapter.py     ← <Name>BackendAdapter with execute(request) → ExecutionResult
  mapper.py      ← check_support(), map_request()
  invoke.py      ← <Name>BackendInvoker
  normalize.py   ← normalize()
  models.py      ← internal types (PreparedRun, RunCapture, etc.)
  errors.py      ← error categorization
```

The public boundary is always:
- **In:** `ExecutionRequest`
- **Out:** `ExecutionResult`
- **Internal:** backend-specific types stay inside the backend namespace
