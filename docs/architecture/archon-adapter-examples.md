# Archon Adapter — Usage Examples

Concrete examples for the Archon backend adapter. All examples use the OperationsCenter canonical contract types.

---

## 1. Basic execution via `ArchonBackendAdapter`

```python
from pathlib import Path
from operations_center.backends.archon.adapter import ArchonBackendAdapter
from operations_center.backends.archon.invoke import StubArchonAdapter, ArchonRunResult

# Use a stub for tests/local dev
stub = StubArchonAdapter(ArchonRunResult(
    outcome="success",
    exit_code=0,
    output_text="archon: workflow complete",
    error_text="",
    workflow_events=[
        {"step": "plan", "status": "ok"},
        {"step": "execute", "status": "ok"},
    ],
))

adapter = ArchonBackendAdapter(stub, workflow_type="goal")
result = adapter.execute(request)  # request: ExecutionRequest

print(result.status)          # ExecutionStatus.SUCCESS
print(result.success)         # True
print(result.changed_files)   # [] (workspace git diff not run in example)
```

---

## 2. Using the `with_stub()` factory

```python
adapter = ArchonBackendAdapter.with_stub(
    outcome="success",
    output_text="archon: done",
)
result = adapter.execute(request)
assert result.success is True

# Failure scenario
adapter = ArchonBackendAdapter.with_stub(
    outcome="failure",
    error_text="validation failed: ruff found 3 errors",
)
result = adapter.execute(request)
assert result.status == ExecutionStatus.FAILED
assert result.failure_category == FailureReasonCategory.VALIDATION_FAILED
```

---

## 3. Capturing workflow events for observability

```python
from operations_center.backends.archon.adapter import ArchonBackendAdapter
from operations_center.observability.models import BackendDetailRef

result, capture = adapter.execute_and_capture(request)

if capture is not None:
    # workflow_events are available for observability retention
    detail_ref = BackendDetailRef(
        detail_type="archon_workflow_events",
        description=f"{len(capture.workflow_events)} workflow steps",
    )
    # capture.workflow_events never goes into ExecutionResult
    print(capture.workflow_events)
    # [{"step": "plan", "status": "ok"}, {"step": "execute", "status": "ok"}]

# ExecutionResult has no workflow_events
assert not hasattr(result, "workflow_events")
```

---

## 4. Checking support before dispatch

```python
from operations_center.backends.archon.mapper import check_support

check = check_support(request)
if not check.supported:
    print(f"Archon cannot handle this request: {check.reason}")
    print(f"Unsupported fields: {check.unsupported_fields}")
    # ["goal_text"] — if goal_text was empty
```

---

## 5. Mapping an `ExecutionRequest` to `ArchonWorkflowConfig`

```python
from operations_center.backends.archon.mapper import map_request

config = map_request(request, workflow_type="fix_pr")

print(config.workflow_type)       # "fix_pr"
print(config.goal_text)           # from request.goal_text
print(config.repo_path)           # from request.workspace_path
print(config.metadata["proposal_id"])  # from request.proposal_id
```

---

## 6. Unsupported request returns UNSUPPORTED_REQUEST, not an exception

```python
from operations_center.contracts.execution import ExecutionRequest
from operations_center.contracts.enums import ExecutionStatus, FailureReasonCategory

bad_request = ExecutionRequest(
    proposal_id="prop-1",
    decision_id="dec-1",
    goal_text="",            # ← empty goal
    repo_key="auth-service",
    clone_url="https://git.example.com/auth.git",
    base_branch="main",
    task_branch="auto/refactor-login",
    workspace_path=Path("/tmp/repo"),
)

result, capture = adapter.execute_and_capture(bad_request)

assert result.status == ExecutionStatus.FAILED
assert result.failure_category == FailureReasonCategory.UNSUPPORTED_REQUEST
assert capture is None  # invocation never ran
```

---

## 7. Timeout handling

```python
from operations_center.backends.archon.invoke import StubArchonAdapter, ArchonRunResult

timeout_stub = StubArchonAdapter(ArchonRunResult(
    outcome="timeout",
    exit_code=1,
    output_text="archon: executing...",
    error_text="[timeout: process killed after 300s]",
    workflow_events=[],
))

adapter = ArchonBackendAdapter(timeout_stub)
result = adapter.execute(request)

assert result.status == ExecutionStatus.TIMEOUT
assert result.failure_category == FailureReasonCategory.TIMEOUT
```

---

## 8. Failure category signals

| error_text content              | `failure_category`         |
|---------------------------------|----------------------------|
| `"[timeout: ..."` or `outcome="timeout"` | `TIMEOUT`         |
| `"no changes detected"`         | `NO_CHANGES`               |
| `"nothing to commit"`           | `NO_CHANGES`               |
| `"merge conflict in src/..."`   | `CONFLICT`                 |
| `"validation failed: ..."`      | `VALIDATION_FAILED`        |
| `"checks failed"`               | `VALIDATION_FAILED`        |
| anything else                   | `BACKEND_ERROR`            |

---

## 9. Direct invocation via `ArchonBackendInvoker`

```python
from operations_center.backends.archon.invoke import ArchonBackendInvoker
from operations_center.backends.archon.mapper import map_request

config = map_request(request)
invoker = ArchonBackendInvoker(adapter=stub)
capture = invoker.invoke(config)

print(capture.run_id)            # "run-abc123"
print(capture.outcome)           # "success"
print(capture.duration_ms)       # measured wall time
print(capture.timeout_hit)       # False
print(capture.artifacts)         # [ArchonArtifactCapture(label="archon log", ...)]
```

---

## 10. Normalizing a capture to `ExecutionResult`

```python
from operations_center.backends.archon.normalize import normalize

result = normalize(
    capture,
    proposal_id=request.proposal_id,
    decision_id=request.decision_id,
    branch_name=request.task_branch,
    workspace_path=request.workspace_path,
    validation_ran=True,
    validation_passed=True,
    validation_duration_ms=800,
)

print(result.status)             # ExecutionStatus.SUCCESS
print(result.validation.status)  # ValidationStatus.PASSED
print(result.artifacts)          # [ExecutionArtifact(artifact_type=LOG_EXCERPT, ...)]
```
