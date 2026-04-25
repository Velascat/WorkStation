# Execution Observability Examples

Concrete examples of how execution results flow through the observability
layer into retained records and inspectable traces.

---

## Example 1 — Successful run with rich artifacts

**ExecutionResult (input):**
```python
ExecutionResult(
    run_id="run-rich-01",
    proposal_id="prop-0001",
    decision_id="dec-0001",
    status=ExecutionStatus.SUCCESS,
    success=True,
    changed_files=[
        ChangedFileRef(path="src/main.py", change_type="modified"),
        ChangedFileRef(path="src/utils.py", change_type="modified"),
    ],
    diff_stat_excerpt="2 files changed, 14 insertions(+), 3 deletions(-)",
    validation=ValidationSummary(
        status=ValidationStatus.PASSED,
        commands_run=2,
        commands_passed=2,
    ),
    artifacts=[
        ExecutionArtifact(artifact_type=ArtifactType.DIFF, label="pre-merge diff", content="..."),
        ExecutionArtifact(artifact_type=ArtifactType.VALIDATION_REPORT, label="ruff output", content="All checks passed."),
        ExecutionArtifact(artifact_type=ArtifactType.LOG_EXCERPT, label="kodo run log", content="kodo: done"),
    ],
)
```

**ExecutionRecord (after recording):**
```
changed_files_evidence:
  status: KNOWN
  source: backend_manifest
  files: [src/main.py, src/utils.py]
  confidence: 1.0

validation_evidence:
  status: PASSED
  checks_run: 2 / checks_passed: 2

artifact_index:
  primary:      [diff, validation_report]
  supplemental: [log_excerpt]
```

**ExecutionTrace:**
```
headline: SUCCESS | kodo @ claude_cli | run=run-rich
summary:  Run run-rich; changed 2 files; 2 files changed, 14 insertions(+), 3 deletions(-); validation=passed (2/2 passed)
warnings: []
```

---

## Example 2 — Failed run with logs but no main artifact

**ExecutionResult (input):**
```python
ExecutionResult(
    run_id="run-fail-01",
    status=ExecutionStatus.FAILED,
    success=False,
    changed_files=[],
    failure_category=FailureReasonCategory.BACKEND_ERROR,
    failure_reason="kodo exited 1: tool call failed",
    artifacts=[
        ExecutionArtifact(artifact_type=ArtifactType.LOG_EXCERPT, label="kodo run log", content="kodo: exit 1"),
    ],
)
```

**ExecutionRecord:**
```
changed_files_evidence:
  status: UNKNOWN
  source: none
  confidence: 0.0

validation_evidence:
  status: SKIPPED

artifact_index:
  primary:      []
  supplemental: [log_excerpt]
```

**ExecutionTrace:**
```
headline: FAILED | kodo @ claude_cli | run=run-fail
summary:  Run run-fail; failed: kodo exited 1: tool call failed
warnings:
  - changed-file manifest unavailable; backend did not report file changes
  - validation was skipped for this run
  - no primary artifacts produced by this run
```

---

## Example 3 — Run with unknown changed files (success, no manifest)

Backend completed successfully but did not call `git diff` (e.g. a future
backend that doesn't run file tracking).

**ExecutionResult (input):**
```python
ExecutionResult(
    run_id="run-unknown-cf-01",
    status=ExecutionStatus.SUCCESS,
    success=True,
    changed_files=[],           # empty, not because no changes, but because unknown
    failure_category=None,
    artifacts=[],
)
```

**ExecutionRecord:**
```
changed_files_evidence:
  status: UNKNOWN
  source: none
  confidence: 0.0
```

**ExecutionTrace:**
```
summary:  Run run-unkn; succeeded
warnings:
  - changed-file manifest unavailable; backend did not report file changes
  - validation was skipped for this run
  - no primary artifacts produced by this run
```

Key point: `UNKNOWN` is not the same as `NONE`. The system does not pretend
the run had no effect.

---

## Example 4 — NO_CHANGES: backend confirmed nothing changed

```python
ExecutionResult(
    run_id="run-nochange-01",
    status=ExecutionStatus.FAILED,
    success=False,
    changed_files=[],
    failure_category=FailureReasonCategory.NO_CHANGES,
    failure_reason="kodo: no changes detected",
)
```

**ExecutionRecord:**
```
changed_files_evidence:
  status: NONE
  source: backend_confirmed_empty
  confidence: 1.0
  notes: "Backend confirmed no files were changed."
```

**ExecutionTrace:**
```
warnings:
  - validation was skipped for this run
  - no primary artifacts produced by this run
  - run completed with no file changes
```

The `NONE` state means: the backend confirmed zero changes. This is distinct
from `UNKNOWN` (backend silent about it).

---

## Example 5 — Partial validation evidence

Run succeeded but validation found errors.

```python
ExecutionResult(
    run_id="run-partial-val-01",
    status=ExecutionStatus.FAILED,
    success=False,
    changed_files=[ChangedFileRef(path="src/api.py", change_type="modified")],
    validation=ValidationSummary(
        status=ValidationStatus.FAILED,
        commands_run=3,
        commands_passed=2,
        commands_failed=1,
        failure_excerpt="mypy: error: Argument 1 has incompatible type",
    ),
    failure_category=FailureReasonCategory.VALIDATION_FAILED,
    artifacts=[
        ExecutionArtifact(artifact_type=ArtifactType.VALIDATION_REPORT, label="mypy output", content="..."),
    ],
)
```

**ExecutionRecord:**
```
changed_files_evidence:
  status: KNOWN
  files: [src/api.py]

validation_evidence:
  status: FAILED
  checks_run: 3 / checks_passed: 2 / checks_failed: 1
  summary: "mypy: error: Argument 1 has incompatible type"
```

**ExecutionTrace:**
```
headline: FAILED | kodo @ claude_cli | run=run-part
summary:  Run run-part; failed: validation failed: mypy errors detected; validation=failed (2/3 passed)
key_artifacts: [validation_report]
warnings:
  - no primary artifacts produced by this run
```

Note: `validation_report` is primary — it IS surfaced in `key_artifacts`.

---

## Example 6 — Adapter-unsupported execution

```python
ExecutionResult(
    run_id="run-blocked-01",
    status=ExecutionStatus.FAILED,
    success=False,
    failure_category=FailureReasonCategory.UNSUPPORTED_REQUEST,
    failure_reason="Request not supported by kodo adapter: goal_text is empty",
    artifacts=[],
)
```

**ExecutionRecord:**
```
changed_files_evidence:
  status: NOT_APPLICABLE
  source: adapter_unsupported
  notes: "Execution did not run because the selected adapter could not support the request."
```

**ExecutionTrace:**
```
changed_files_summary: not applicable (execution did not run)
warnings:
  - validation was skipped for this run
  - no primary artifacts produced by this run
```

No changed-file warning for NOT_APPLICABLE — the system understands
execution did not run.

---

## Example 7 — Attaching raw backend detail references

```python
from operations_center.observability.models import BackendDetailRef
from operations_center.observability.service import ExecutionObservabilityService

svc = ExecutionObservabilityService.default()

refs = [
    BackendDetailRef(
        detail_type="stderr_log",
        path="/tmp/workspaces/run-abc/stderr.txt",
        description="kodo stderr captured during run",
        is_required_for_debug=True,
    ),
    BackendDetailRef(
        detail_type="jsonl_stream",
        path="/tmp/workspaces/run-abc/events.jsonl",
        description="kodo JSONL event stream",
    ),
]

record, trace = svc.observe(
    result,
    backend="kodo",
    lane="claude_cli",
    raw_detail_refs=refs,
    notes="nightly lint cycle",
    metadata={"trigger": "cron", "repo": "api-service"},
)

# Raw refs are retained in the record, not inlined into canonical summary
assert len(record.backend_detail_refs) == 2
assert record.backend_detail_refs[0].detail_type == "stderr_log"

# Trace also carries the refs for easy access during triage
assert len(trace.backend_detail_refs) == 2
```

---

## Example 8 — Minimal (sparse) backend produces a valid record

Even if a future backend produces the absolute minimum ExecutionResult,
the observability layer produces a valid, complete record.

```python
result = ExecutionResult(
    run_id="run-sparse-01",
    proposal_id="prop-0001",
    decision_id="dec-0001",
    status=ExecutionStatus.FAILED,
    success=False,
    failure_category=FailureReasonCategory.UNKNOWN,
)

record, trace = ExecutionObservabilityService.default().observe(result)

assert record.artifact_index is not None
assert record.changed_files_evidence.status == ChangedFilesStatus.UNKNOWN
assert record.validation_evidence.status == ValidationStatus.SKIPPED
assert isinstance(trace, ExecutionTrace)
assert len(trace.warnings) > 0
```

No field requires special backend richness. Sparse backends degrade gracefully.
