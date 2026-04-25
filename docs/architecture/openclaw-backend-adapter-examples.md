# OpenClaw Backend Adapter — Examples

## Supported request → successful result with known changed files

```python
from pathlib import Path
from operations_center.backends.openclaw import OpenClawBackendAdapter
from operations_center.contracts.execution import ExecutionRequest

adapter = OpenClawBackendAdapter.with_stub(
    outcome="success",
    output_text="openclaw: fixed 3 lint errors",
)

request = ExecutionRequest(
    proposal_id="prop-001",
    decision_id="dec-001",
    goal_text="Fix all lint errors in src/",
    repo_key="api-service",
    clone_url="https://github.com/example/api.git",
    base_branch="main",
    task_branch="auto/fix-lint-abc123",
    workspace_path=Path("/workspace/api-service"),
)

result = adapter.execute(request)
print(result.status)   # ExecutionStatus.SUCCESS
print(result.success)  # True
# When git diff succeeds on workspace_path:
# result.changed_files → [ChangedFileRef(path="src/main.py", change_type="modified")]
```

## Retaining raw events for observability

```python
result, capture = adapter.execute_and_capture(request)

print(capture.event_count)            # number of OpenClaw events
print(capture.changed_files_source)   # "git_diff" | "event_stream" | "unknown"
print(capture.events)                 # raw event list — NOT in ExecutionResult

# Store events as BackendDetailRef via observability layer:
from operations_center.observability.models import BackendDetailRef
import json, tempfile, pathlib

if capture.events:
    tmp = pathlib.Path(tempfile.mkdtemp()) / "openclaw_events.json"
    tmp.write_text(json.dumps(capture.events))
    ref = BackendDetailRef(
        detail_type="event_trace",
        path=str(tmp),
        description=f"{len(capture.events)} OpenClaw events",
    )
    # pass ref to ExecutionRecorder.record(..., raw_detail_refs=[ref])
```

## Inferred changed files from event stream

When git diff is unavailable (no workspace or git not initialized), OpenClaw's
reported files are used as an inferred fallback:

```python
# OpenClaw reported the files it wrote in its event stream:
adapter = OpenClawBackendAdapter.with_stub(
    outcome="success",
    reported_changed_files=[
        {"path": "src/auth.py",        "change_type": "modified"},
        {"path": "tests/test_auth.py", "change_type": "modified"},
    ],
)

result, capture = adapter.execute_and_capture(request)

print(capture.changed_files_source)   # "event_stream" (inferred)
print(len(result.changed_files))      # 2 — populated from event stream

# The observability layer sees changed_files_source="event_stream" and can
# record this as lower-confidence evidence rather than authoritative git diff.
```

## Unknown changed files

When neither git diff nor OpenClaw-reported files are available:

```python
adapter = OpenClawBackendAdapter.with_stub(outcome="success")

# workspace_path points to a directory without git:
result, capture = adapter.execute_and_capture(
    ExecutionRequest(..., workspace_path=Path("/no-git/workspace"))
)

print(capture.changed_files_source)   # "unknown"
print(result.changed_files)           # []  — empty, never pretends certainty
```

## Unsupported request → graceful rejection

```python
# Request with empty goal_text is rejected before invocation:
bad_request = ExecutionRequest(
    ...
    goal_text="",   # empty
)

check = adapter.supports(bad_request)
print(check.supported)         # False
print(check.unsupported_fields) # ["goal_text"]

result = adapter.execute(bad_request)
print(result.failure_category)  # FailureReasonCategory.UNSUPPORTED_REQUEST
# OpenClaw was never invoked.
```

## Failure with error detail

```python
adapter = OpenClawBackendAdapter.with_stub(
    outcome="failure",
    error_text="tool call raised an unhandled exception",
)

result = adapter.execute(request)
print(result.status)           # ExecutionStatus.FAILED
print(result.failure_category) # FailureReasonCategory.BACKEND_ERROR
print(result.failure_reason)   # "openclaw failed: tool call raised..."
```

## Timeout

```python
adapter = OpenClawBackendAdapter.with_stub(outcome="timeout")

result = adapter.execute(request)
print(result.status)           # ExecutionStatus.TIMEOUT
print(result.failure_category) # FailureReasonCategory.TIMEOUT
```

## No-changes outcome

```python
adapter = OpenClawBackendAdapter.with_stub(
    outcome="failure",
    output_text="no changes detected, working tree clean",
)

result = adapter.execute(request)
print(result.failure_category) # FailureReasonCategory.NO_CHANGES
```

## Using in tests with the stub factory

```python
from operations_center.backends.openclaw import OpenClawBackendAdapter
from pathlib import Path

# Minimal success stub:
adapter = OpenClawBackendAdapter.with_stub()
result = adapter.execute(request)
assert result.success is True

# Stub with events and reported files:
adapter = OpenClawBackendAdapter.with_stub(
    outcome="success",
    events=[{"type": "tool_use", "name": "write_file", "path": "src/a.py"}],
    reported_changed_files=[{"path": "src/a.py", "change_type": "modified"}],
)
result, capture = adapter.execute_and_capture(request)
assert capture.event_count == 1
assert capture.changed_files_source == "event_stream"  # when no workspace
```

## Connecting to a real OpenClaw service

Subclass `OpenClawRunner` to connect to your real implementation:

```python
from operations_center.backends.openclaw.invoke import OpenClawRunner, OpenClawRunResult
from operations_center.backends.openclaw.models import OpenClawPreparedRun
from operations_center.backends.openclaw import OpenClawBackendAdapter

class MyOpenClawRunner(OpenClawRunner):
    def run(self, prepared: OpenClawPreparedRun) -> OpenClawRunResult:
        # your implementation here: subprocess, RPC, Python API, etc.
        ...
        return OpenClawRunResult(
            outcome="success",
            exit_code=0,
            output_text=stdout,
            events=event_list,
            reported_changed_files=file_list,
        )

adapter = OpenClawBackendAdapter(runner=MyOpenClawRunner())
result = adapter.execute(request)
```

## What the adapter does NOT do

- It does not select routes or lanes (SwitchBoard owns that)
- It does not invoke the outer-shell layer (`openclaw_shell/`)
- It does not define canonical contracts
- It does not store execution records (observability layer owns that)
- It does not pretend changed-file lists are authoritative when they are inferred
