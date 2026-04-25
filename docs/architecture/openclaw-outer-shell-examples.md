# OpenClaw Outer Shell — Examples

## Triggering a Run

```python
from operations_center.openclaw_shell.bridge import OpenClawBridge
from operations_center.openclaw_shell.models import OperatorContext

bridge = OpenClawBridge.default()

ctx = OperatorContext(
    goal_text="Fix all lint errors in the API package",
    repo_key="api-service",
    clone_url="https://github.com/example/api-service.git",
    base_branch="main",
    risk_level="low",
    labels=["lint_fix"],
    timeout_seconds=300,
)

handle = bridge.trigger(ctx)

print(handle.selected_lane)     # "claude_cli"
print(handle.selected_backend)  # "kodo"
print(handle.status)            # "planned"
print(handle.routing_confidence) # 0.9
```

## Triggering and Getting a Route Summary

```python
handle, summary = bridge.trigger_with_summary(ctx)

print(summary.headline)    # "PLANNED | claude_cli @ kodo"
print(summary.success)     # False — execution hasn't happened yet
print(summary.status)      # "pending"
```

## Deriving Status from an Execution Result

After a backend adapter completes execution and returns an `ExecutionResult`:

```python
# Full path — uses observability layer
summary = bridge.status_from_result(result, lane="claude_cli", backend="kodo")
print(summary.success)               # True
print(summary.headline)              # "SUCCESS | kodo @ claude_cli | run=abc12345"
print(summary.changed_files_status)  # "known"
print(summary.validation_status)     # "passed"
print(summary.artifact_count)        # 2
print(summary.recorded_at)           # datetime(...) — set from observability

# Lightweight path — no observability overhead
summary = bridge.status_from_result_lightweight(result, lane="claude_cli", backend="kodo")
print(summary.recorded_at)   # None — not set in lightweight path
```

## Inspecting a Retained Record

After an execution record has been retained by the observability layer:

```python
from operations_center.observability.recorder import ExecutionRecorder
from operations_center.observability.trace import RunReportBuilder

recorder = ExecutionRecorder()
builder = RunReportBuilder()

record = recorder.record(result, backend="kodo", lane="claude_cli")
trace = builder.build_report(record)

inspection = bridge.inspect_from_record(record, trace)

print(inspection.run_id)               # "run-abc12345"
print(inspection.headline)             # "SUCCESS | kodo @ claude_cli | run=abc12345"
print(inspection.warnings)             # []
print(inspection.artifact_count)       # 2
print(inspection.primary_artifact_count) # 1
print(inspection.changed_files_status) # "known"
print(inspection.validation_status)    # "passed"
print(inspection.trace_id)             # UUID from trace
print(inspection.record_id)            # UUID from record
```

## Wrapping Shell Actions

`wrap_action()` runs a callable and converts its outcome to a `ShellActionResult`. Exceptions are caught and surfaced without propagating.

```python
def do_something_risky():
    raise ValueError("unexpected state")

result = bridge.wrap_action("my_action", do_something_risky)
print(result.success)  # False
print(result.message)  # "unexpected state"
print(result.detail)   # "ValueError"

def do_something_clean():
    pass

result = bridge.wrap_action("clean_action", do_something_clean)
print(result.success)  # True
print(result.message)  # "ok"
```

## Checking the Optionality Flag

```python
import os

os.environ["OPENCLAW_SHELL_ENABLED"] = "1"
print(OpenClawBridge.is_enabled())  # True

os.environ["OPENCLAW_SHELL_ENABLED"] = "0"
print(OpenClawBridge.is_enabled())  # False

# Typical gating pattern in operator code:
if OpenClawBridge.is_enabled():
    bridge = OpenClawBridge.default()
    handle = bridge.trigger(ctx)
else:
    # system continues without the shell layer
    pass
```

## Using Stub Routing in Tests

```python
bridge = OpenClawBridge.with_stub_routing(
    lane="aider_local",
    backend="kodo",
    confidence=0.85,
)

ctx = OperatorContext(goal_text="Refactor utils", repo_key="svc")
handle = bridge.trigger(ctx)

assert handle.selected_lane == "aider_local"
assert handle.selected_backend == "kodo"
assert handle.routing_confidence == pytest.approx(0.85)
```

## OperatorContext with All Fields

```python
ctx = OperatorContext(
    goal_text="Refactor the auth module for compliance",
    repo_key="auth-service",
    task_type="refactor",
    execution_mode="goal",
    clone_url="https://github.com/example/auth-service.git",
    base_branch="main",
    risk_level="medium",
    priority="high",
    constraints_text="Only touch auth/ directory; do not modify tests/",
    labels=["compliance", "priority:high"],
    allowed_paths=["auth/"],
    timeout_seconds=600,
    shell_flags={"dry_run": False, "verbose": True},
    task_id="task-001",
    project_id="proj-auth",
)
```

## What the Shell Does NOT Do

The shell never:

- Invokes a backend directly
- Decides which lane or backend to use (SwitchBoard owns that)
- Stores execution records (observability layer owns that)
- Defines canonical contract types (contracts/ owns that)

The bridge is a projection layer, not an orchestration layer.
