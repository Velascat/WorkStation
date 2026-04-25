# Execution Observability Architecture

How canonical execution outcomes become retained, inspectable records — and
why raw backend details are kept separate from normalized summaries.

---

## Why this layer exists

Without normalized observability, every backend becomes its own source of
truth. Logs differ. Success/failure meanings drift. Changed-file data becomes
unreliable or backend-dependent. Fallback, escalation, and tuning layers would
have to guess from inconsistent raw evidence.

This layer prevents that by making every execution outcome:

- **retained** — normalized to a stable format regardless of backend
- **inspectable** — queryable as a structured record
- **honest** — uncertainty is represented explicitly (changed files may be
  unknown; validation may have been skipped)
- **comparable** — the same model works for kodo, Archon, OpenClaw, etc.

---

## How it relates to ExecutionResult

`ExecutionResult` is the canonical outcome contract — the interface every
backend adapter implements. It is not changed by this layer.

This layer adds:

- `ExecutionRecord` — retained wrapper around `ExecutionResult` with
  classified artifacts, changed-file evidence, and backend detail refs
- `ExecutionTrace` — inspectable report generated from `ExecutionRecord`

```
ExecutionResult + raw backend detail refs
  → ExecutionRecorder
  → ExecutionRecord
  → RunReportBuilder
  → ExecutionTrace + ArtifactIndex
```

`ExecutionRecord` is the primary retained artifact. `ExecutionTrace` is
derived on demand — it is never the primary record.

---

## Module layout

```
src/operations_center/observability/
  __init__.py          — public API
  models.py            — BackendDetailRef, ExecutionRecord
  changed_files.py     — ChangedFilesEvidence, ChangedFilesStatus, normalize_changed_files()
  validation.py        — ValidationEvidence, normalize_validation()
  artifacts.py         — ArtifactIndex, ArtifactNormalizer
  recorder.py          — ExecutionRecorder
  trace.py             — ExecutionTrace, RunReportBuilder
  service.py           — ExecutionObservabilityService (top-level facade)
```

---

## Artifact classification

Artifacts are split into **primary** and **supplemental** categories.

| Type | Category | Rationale |
|---|---|---|
| `diff` | primary | the main code output |
| `patch` | primary | alternative patch form of output |
| `validation_report` | primary | quality evidence |
| `log_excerpt` | supplemental | diagnostic; not the main output |
| `goal_file` | supplemental | input, not output |
| `pr_url` | supplemental | reference metadata |
| `branch_ref` | supplemental | reference metadata |

`ArtifactIndex` holds the classified lists and a per-type count. Primary
artifacts surface in `ExecutionTrace.key_artifacts`; supplemental artifacts
are retained in the record but not promoted to the trace headline.

---

## Changed-file evidence states

Changed-file knowledge is represented with explicit certainty levels.

| Status | Meaning |
|---|---|
| `KNOWN` | Files enumerated by the backend (non-empty list) |
| `NONE` | Backend confirmed no files changed (e.g. `NO_CHANGES` failure category) |
| `UNKNOWN` | Backend did not report; could not determine |
| `NOT_APPLICABLE` | Execution never ran (e.g. `POLICY_BLOCKED`, `UNSUPPORTED_REQUEST`) |

`UNKNOWN` is never coerced into an empty `KNOWN`. Downstream code must handle
uncertainty explicitly.

The `source` field records how the evidence was obtained:

| Source | Meaning |
|---|---|
| `backend_manifest` | Backend produced a non-empty changed-file list |
| `backend_confirmed_empty` | Backend confirmed via `NO_CHANGES` category |
| `policy_blocked` | Execution was blocked before it ran by policy |
| `adapter_unsupported` | Execution never started because the adapter could not support the request |
| `none` | No information available |

---

## Validation evidence

`ValidationEvidence` normalizes `ValidationSummary` from the canonical
contract into an observability-oriented model that also accepts artifact
references.

If validation was skipped (the common case when the kodo adapter runs without
the OperationsCenter execution boundary providing validation results), `ValidationEvidence.status`
is `SKIPPED` — not fabricated as passed.

---

## Raw backend detail separation

Raw backend outputs — stderr logs, JSONL event streams, workspace snapshots,
structured result blobs — are **not** stuffed into canonical telemetry.

Instead, `BackendDetailRef` provides a bounded reference:

```python
BackendDetailRef(
    detail_type="stderr_log",
    path="/tmp/workspaces/run-abc/stderr.txt",
    description="kodo stderr from run run-abc123",
    is_required_for_debug=True,
)
```

`ExecutionRecord.backend_detail_refs` holds a list of these. The raw files
themselves live wherever the backend left them; only the reference is
normalized into the record.

This keeps canonical telemetry small and comparable across backends while
preserving full raw evidence for incident investigation.

---

## Usage

### Basic recording

```python
from operations_center.observability.service import ExecutionObservabilityService

svc = ExecutionObservabilityService.default()
record, trace = svc.observe(
    result,
    backend="kodo",
    lane="claude_cli",
    notes="triggered by Plane watcher",
)

print(trace.headline)
# SUCCESS | kodo @ claude_cli | run=a1b2c3d4

print(trace.summary)
# Run a1b2c3d4; changed 2 files; 2 files changed, 14 insertions(+); validation=passed (2/2 passed)

for w in trace.warnings:
    print(f"[warn] {w}")
```

### With raw detail references

```python
from operations_center.observability.models import BackendDetailRef

refs = [
    BackendDetailRef(
        detail_type="stderr_log",
        path="/tmp/ws/run-abc/stderr.txt",
        is_required_for_debug=True,
    ),
    BackendDetailRef(
        detail_type="workspace_snapshot",
        path="/tmp/ws/run-abc/",
    ),
]
record, trace = svc.observe(result, raw_detail_refs=refs)
# refs retained in record.backend_detail_refs, not inlined into canonical summary
```

### Direct layer use

```python
from operations_center.observability import (
    ArtifactNormalizer,
    ExecutionRecorder,
    RunReportBuilder,
    normalize_changed_files,
    normalize_validation,
)

# classify artifacts
index = ArtifactNormalizer.index(result.artifacts)
print(index.primary_artifacts)
print(index.supplemental_artifacts)

# changed-file certainty
cfe = normalize_changed_files(result)
print(cfe.status)  # KNOWN / NONE / UNKNOWN / NOT_APPLICABLE

# build record
recorder = ExecutionRecorder()
record = recorder.record(result, backend="kodo")

# build trace
builder = RunReportBuilder()
trace = builder.build_report(record)
```

---

## What this layer does not own

- Backend invocation — that is the backend adapter's job
- Backend selection — that is SwitchBoard's job
- Proposal generation — that is OperationsCenter's planning layer
- Persisting to a database — filesystem-local retention is sufficient
- Dashboard productization — out of scope
- Universal log ingestion for every possible future signal

---

## Ownership table

| Concern | Owner |
|---|---|
| Normalized execution records | `OperationsCenter: observability/recorder.py` |
| Artifact classification | `OperationsCenter: observability/artifacts.py` |
| Changed-file certainty | `OperationsCenter: observability/changed_files.py` |
| Validation normalization | `OperationsCenter: observability/validation.py` |
| Inspectable traces | `OperationsCenter: observability/trace.py` |
| Raw backend detail capture | Backend adapter (e.g. `backends/kodo/normalize.py`) |
| Backend output format | Each backend adapter, internally |

---

## See also

- [contracts.md](contracts.md) — ExecutionResult, ExecutionArtifact, ValidationSummary
- [kodo-adapter.md](kodo-adapter.md) — how kodo populates ExecutionResult
- [operations-center-routing.md](operations-center-routing.md) — PlanningService and ProposalDecisionBundle
