# Canonical Cross-Repo Contracts

This document defines the platform's canonical data contracts — the typed,
backend-agnostic models that structure communication between ControlPlane,
SwitchBoard, and execution backends (kodo, Archon, etc.).

---

## What contracts are

Contracts are Pydantic v2 models that travel across component boundaries.
They are:

- **Backend-agnostic** — they do not reference kodo, Archon, or any specific runner
- **Serialisable** — all fields round-trip cleanly through JSON
- **Validated** — Pydantic enforces field constraints at construction time
- **Frozen** — all contract models are immutable after construction

Contracts are not internal domain models. ControlPlane has internal models
(`BoardTask`, `RepoTarget`) that are Plane-workflow-specific and stay inside
ControlPlane. Contracts are the surface where components meet.

---

## Canonical ownership

> Contracts live in ControlPlane (`src/control_plane/contracts/`).

ControlPlane is the upstream origin of all work in the system. It proposes
tasks, it consumes results. Locating contracts here avoids circular dependencies:
SwitchBoard and kodo consume contracts but do not produce them upstream.

When contracts need to be consumed in SwitchBoard or a backend adapter, they are
imported from a stable release of the `control-plane` package or vendored as
a separate `platform-contracts` package (future phase). For now, the source of
truth is `src/control_plane/contracts/`.

---

## Module layout

```
src/control_plane/contracts/
├── __init__.py      — public API, re-exports all canonical types
├── enums.py         — TaskType, LaneName, BackendName, ExecutionStatus, ...
├── common.py        — TaskTarget, ExecutionConstraints, ValidationProfile,
│                       BranchPolicy, ChangedFileRef, ValidationSummary
├── proposal.py      — TaskProposal
├── routing.py       — LaneDecision
└── execution.py     — ExecutionRequest, ExecutionArtifact,
                        RunTelemetry, ExecutionResult
```

---

## Contract models

### TaskProposal

Emitted by ControlPlane when it decides a task is worth attempting.

| Field | Type | Description |
|-------|------|-------------|
| `proposal_id` | str (uuid) | Unique proposal identifier |
| `task_id` | str | Upstream task ID (Plane board task) |
| `project_id` | str | Project the task belongs to |
| `task_type` | TaskType | Category: lint_fix, bug_fix, documentation, … |
| `execution_mode` | ExecutionMode | Strategy: goal, fix_pr, test_campaign, … |
| `goal_text` | str | Natural-language goal description |
| `constraints_text` | str? | Natural-language constraints |
| `target` | TaskTarget | Repo, branch, allowed paths |
| `priority` | Priority | low / normal / high / critical |
| `risk_level` | RiskLevel | ControlPlane's risk estimate |
| `constraints` | ExecutionConstraints | Timeout, max files, validation policy |
| `validation_profile` | ValidationProfile | Commands to run, fail-fast flag |
| `branch_policy` | BranchPolicy | Branch prefix, push-on-success, open-PR |
| `proposed_at` | datetime | UTC timestamp |
| `proposer` | str? | Component that created the proposal |
| `labels` | list[str] | Free-form tags |

**Invariants:** Frozen. `proposal_id` is auto-generated UUID. `priority` defaults
to `normal`, `risk_level` to `low`.

---

### LaneDecision

Emitted by SwitchBoard in response to a TaskProposal.

| Field | Type | Description |
|-------|------|-------------|
| `decision_id` | str (uuid) | Unique decision identifier |
| `proposal_id` | str | Reference to the originating proposal |
| `selected_lane` | LaneName | claude_cli / codex_cli / aider_local |
| `selected_backend` | BackendName | kodo / archon / openclaw |
| `confidence` | float [0–1] | Routing confidence |
| `policy_rule_matched` | str? | Name of the policy rule that fired |
| `rationale` | str? | Human-readable explanation |
| `alternatives_considered` | list[LaneName] | Other lanes evaluated |
| `decided_at` | datetime | UTC timestamp |
| `switchboard_version` | str? | SwitchBoard version for audit |

**Invariants:** Frozen. References proposal by ID only — does not embed the proposal.

---

### ExecutionRequest

Produced by the lane runner after receiving a TaskProposal + LaneDecision.
Contains everything the backend adapter needs, including execution-layer details
(workspace path, branch name) that are not present in the proposal.

| Field | Type | Description |
|-------|------|-------------|
| `run_id` | str (uuid) | Unique run identifier |
| `proposal_id` | str | Originating proposal |
| `decision_id` | str | Originating decision |
| `goal_text` | str | Resolved from proposal |
| `constraints_text` | str? | Resolved from proposal |
| `repo_key` | str | Logical repo name |
| `clone_url` | str | Git clone URL |
| `base_branch` | str | Source branch for the task branch |
| `task_branch` | str | Branch created for this run |
| `workspace_path` | Path | Absolute path to checked-out workspace |
| `goal_file_path` | Path? | Path to goal file in workspace |
| `allowed_paths` | list[str] | Paths the backend may modify |
| `max_changed_files` | int? | Abort threshold |
| `timeout_seconds` | int | Wall-clock execution limit |
| `require_clean_validation` | bool | Fail if validation commands fail |
| `validation_commands` | list[str] | Commands to run after execution |
| `requested_at` | datetime | UTC timestamp |

---

### ExecutionArtifact

A discrete artifact produced during execution — diff, patch, report, log excerpt.

| Field | Type | Description |
|-------|------|-------------|
| `artifact_id` | str (uuid) | Unique identifier |
| `artifact_type` | ArtifactType | diff, patch, validation_report, log_excerpt, … |
| `label` | str | Short human-readable label |
| `content` | str? | Inline content (small artifacts) |
| `uri` | str? | External URI (large artifacts) |
| `size_bytes` | int? | Size |
| `produced_at` | datetime | UTC timestamp |

---

### RunTelemetry

Timing and resource data for one execution run. Separated from ExecutionResult
to keep the result clean for routing/retry logic.

| Field | Type | Description |
|-------|------|-------------|
| `run_id` | str | Matches ExecutionResult.run_id |
| `started_at` / `finished_at` | datetime | Execution wall-clock bounds |
| `duration_ms` | int | Wall-clock duration |
| `llm_calls` | int | Total LLM API calls made |
| `llm_input_tokens` | int | Total input tokens consumed |
| `llm_output_tokens` | int | Total output tokens produced |
| `tool_calls` | int | Total tool invocations |
| `lane_name` | str? | Lane that executed the run |
| `backend_name` | str? | Backend adapter name |
| `backend_version` | str? | Backend version string |
| `labels` | dict[str, str] | Free-form backend labels |

---

### ExecutionResult

The canonical outcome returned by any backend adapter.

| Field | Type | Description |
|-------|------|-------------|
| `run_id` | str | Matches ExecutionRequest.run_id |
| `proposal_id` | str | Originating proposal |
| `decision_id` | str | Originating decision |
| `status` | ExecutionStatus | pending / running / success / failed / … |
| `success` | bool | True only when status == success |
| `changed_files` | list[ChangedFileRef] | Files changed during execution |
| `diff_stat_excerpt` | str? | Short diff summary for display |
| `validation` | ValidationSummary | Aggregated validation outcome |
| `branch_pushed` | bool | Whether the task branch was pushed |
| `branch_name` | str? | Task branch name |
| `pull_request_url` | str? | PR URL if opened |
| `failure_category` | FailureReasonCategory? | Coarse failure classification |
| `failure_reason` | str? | Human-readable failure explanation |
| `artifacts` | list[ExecutionArtifact] | Attached artifacts |
| `completed_at` | datetime | UTC timestamp |

---

## Supporting enums

| Enum | Values |
|------|--------|
| `TaskType` | lint_fix, bug_fix, simple_edit, test_write, documentation, refactor, feature, dependency_update, unknown |
| `LaneName` | claude_cli, codex_cli, aider_local |
| `BackendName` | kodo, archon, openclaw |
| `ExecutionMode` | goal, fix_pr, test_campaign, improve_campaign |
| `ExecutionStatus` | pending, running, success, failed, skipped, timeout, cancelled |
| `ArtifactType` | diff, patch, validation_report, log_excerpt, goal_file, pr_url, branch_ref |
| `ValidationStatus` | passed, failed, skipped, error |
| `RiskLevel` | low, medium, high |
| `Priority` | low, normal, high, critical |
| `FailureReasonCategory` | validation_failed, backend_error, timeout, no_changes, conflict, policy_blocked, unknown |

---

## Supporting value objects

| Type | Purpose |
|------|---------|
| `TaskTarget` | Repo key, clone URL, base branch, allowed paths |
| `ExecutionConstraints` | Timeout, max changed files, validation policy flags |
| `ValidationProfile` | Commands, timeout, fail-fast flag |
| `BranchPolicy` | Branch prefix, push-on-success, open-PR, allowed base branches |
| `ChangedFileRef` | File path, change type, line stats |
| `ValidationSummary` | Aggregated validation outcome with counts and excerpt |

---

## Design principles

**Frozen models.** All contract types use `model_config = {"frozen": True}`.
Contracts represent facts that happened or decisions that were made. They should
not be mutated after construction.

**str-based enums.** All enums extend `str`. This means enum values pass `json.dumps`
without a custom serialiser and display as plain strings in logs.

**No internal types in contracts.** Contracts do not reference ControlPlane's
internal domain types (`BoardTask`, `RepoTarget`). Those live in
`src/control_plane/domain/models.py` and are ControlPlane-internal.

**Auto-generated IDs.** `proposal_id`, `decision_id`, `run_id`, and `artifact_id`
are UUID strings generated at construction time. Callers can override them to
provide externally-tracked IDs.

**Optional telemetry.** `RunTelemetry` is a separate model so that backends that
do not track token counts or tool calls can omit it without polluting the
result model.

---

## What this phase intentionally leaves unimplemented

Phase 3 defines the contract types. The following are deferred:

- **Cross-repo import distribution** — packaging contracts as a standalone
  `platform-contracts` installable is a Phase 4–5 concern.
- **SwitchBoard adapter wiring** — SwitchBoard does not yet import these types
  for its domain models. That requires Phase 4 contract adoption.
- **ControlPlane emission** — ControlPlane does not yet emit `TaskProposal` from
  its proposer; it continues to use its internal `BoardTask`/`ExecutionRequest`
  models. Adopting contracts is Phase 4–5 migration work.
- **Backend adapter implementation** — kodo and Archon adapters that accept
  `ExecutionRequest` and return `ExecutionResult` are future scope.
