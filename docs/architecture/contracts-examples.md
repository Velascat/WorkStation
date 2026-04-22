# Contract Examples

Concrete JSON payloads for each canonical contract. Use these as reference
when building adapters, writing tests, or verifying serialisation.

---

## TaskProposal

A lint-fix proposal for a small service repo, low risk, standard priority:

```json
{
  "proposal_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "task_id": "TASK-1042",
  "project_id": "proj-backend",
  "task_type": "lint_fix",
  "execution_mode": "goal",
  "goal_text": "Fix all ruff lint errors in src/. Do not change logic.",
  "constraints_text": "Only modify files under src/. Do not touch tests/.",
  "target": {
    "repo_key": "api-service",
    "clone_url": "https://github.com/org/api-service.git",
    "base_branch": "main",
    "allowed_paths": ["src/**"]
  },
  "priority": "normal",
  "risk_level": "low",
  "constraints": {
    "max_changed_files": 20,
    "timeout_seconds": 300,
    "allowed_paths": ["src/**"],
    "require_clean_validation": true,
    "skip_baseline_validation": false
  },
  "validation_profile": {
    "profile_name": "lint_only",
    "commands": ["ruff check src/"],
    "timeout_seconds": 60,
    "fail_fast": true
  },
  "branch_policy": {
    "branch_prefix": "auto/",
    "push_on_success": true,
    "open_pr": false,
    "allowed_base_branches": ["main"]
  },
  "proposed_at": "2026-04-22T09:00:00Z",
  "proposer": "control-plane",
  "labels": ["lint", "automated"]
}
```

A feature proposal with higher risk and a PR requirement:

```json
{
  "proposal_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "task_id": "TASK-2001",
  "project_id": "proj-auth",
  "task_type": "feature",
  "execution_mode": "goal",
  "goal_text": "Add rate limiting middleware to /api/login. See goal file for spec.",
  "constraints_text": null,
  "target": {
    "repo_key": "auth-service",
    "clone_url": "https://github.com/org/auth-service.git",
    "base_branch": "main",
    "allowed_paths": []
  },
  "priority": "high",
  "risk_level": "medium",
  "constraints": {
    "max_changed_files": null,
    "timeout_seconds": 600,
    "allowed_paths": [],
    "require_clean_validation": true,
    "skip_baseline_validation": false
  },
  "validation_profile": {
    "profile_name": "strict",
    "commands": ["ruff check .", "pytest tests/ -x"],
    "timeout_seconds": 300,
    "fail_fast": true
  },
  "branch_policy": {
    "branch_prefix": "auto/",
    "push_on_success": true,
    "open_pr": true,
    "allowed_base_branches": ["main", "develop"]
  },
  "proposed_at": "2026-04-22T14:30:00Z",
  "proposer": "control-plane",
  "labels": ["feature", "auth", "review-required"]
}
```

---

## LaneDecision

Routing a low-risk lint proposal to the local lane:

```json
{
  "decision_id": "c3d4e5f6-a7b8-9012-cdef-012345678902",
  "proposal_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "selected_lane": "aider_local",
  "selected_backend": "kodo",
  "confidence": 0.97,
  "policy_rule_matched": "low-risk-to-local",
  "rationale": "task_type=lint_fix, risk_level=low: local lane is preferred for zero-cost execution",
  "alternatives_considered": ["claude_cli"],
  "decided_at": "2026-04-22T09:00:01Z",
  "switchboard_version": "0.4.2"
}
```

Routing a high-risk feature to the premium lane:

```json
{
  "decision_id": "d4e5f6a7-b8c9-0123-def0-123456789003",
  "proposal_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "selected_lane": "claude_cli",
  "selected_backend": "kodo",
  "confidence": 0.88,
  "policy_rule_matched": "medium-risk-to-premium",
  "rationale": "task_type=feature, risk_level=medium: premium lane required by policy",
  "alternatives_considered": ["codex_cli", "aider_local"],
  "decided_at": "2026-04-22T14:30:01Z",
  "switchboard_version": "0.4.2"
}
```

---

## ExecutionRequest

Resolved from a lint proposal after the lane runner sets up a workspace:

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
  "goal_file_path": "/home/dev/workspaces/api-service-e5f6a7b8/.goal.md",
  "allowed_paths": ["src/**"],
  "max_changed_files": 20,
  "timeout_seconds": 300,
  "require_clean_validation": true,
  "validation_commands": ["ruff check src/"],
  "requested_at": "2026-04-22T09:00:02Z"
}
```

---

## ExecutionArtifact

A diff artifact with inline content:

```json
{
  "artifact_id": "f6a7b8c9-d0e1-2345-f012-345678900005",
  "artifact_type": "diff",
  "label": "final diff",
  "content": "--- a/src/main.py\n+++ b/src/main.py\n@@ -12,7 +12,7 @@\n-x=1\n+x = 1\n",
  "uri": null,
  "size_bytes": 74,
  "produced_at": "2026-04-22T09:01:30Z"
}
```

A validation report stored externally:

```json
{
  "artifact_id": "a7b8c9d0-e1f2-3456-0123-456789000006",
  "artifact_type": "validation_report",
  "label": "ruff check output",
  "content": null,
  "uri": "s3://platform-artifacts/runs/e5f6a7b8/validation.json",
  "size_bytes": 4120,
  "produced_at": "2026-04-22T09:01:45Z"
}
```

---

## RunTelemetry

Telemetry for a local Aider run:

```json
{
  "run_id": "e5f6a7b8-c9d0-1234-ef01-234567890004",
  "started_at": "2026-04-22T09:00:02Z",
  "finished_at": "2026-04-22T09:01:52Z",
  "duration_ms": 110000,
  "llm_calls": 4,
  "llm_input_tokens": 12400,
  "llm_output_tokens": 820,
  "tool_calls": 11,
  "lane_name": "aider_local",
  "backend_name": "kodo",
  "backend_version": "0.3.1",
  "labels": {
    "model": "qwen2.5-coder:1.5b",
    "aider_version": "0.52.0"
  }
}
```

Telemetry for a Claude CLI run:

```json
{
  "run_id": "f7a8b9c0-d1e2-3456-0123-567890100007",
  "started_at": "2026-04-22T14:30:02Z",
  "finished_at": "2026-04-22T14:37:44Z",
  "duration_ms": 462000,
  "llm_calls": 23,
  "llm_input_tokens": 98500,
  "llm_output_tokens": 7800,
  "tool_calls": 67,
  "lane_name": "claude_cli",
  "backend_name": "kodo",
  "backend_version": "0.3.1",
  "labels": {
    "claude_model": "claude-sonnet-4-6",
    "session_id": "sess-abc123"
  }
}
```

---

## ExecutionResult

Successful lint fix with diff and validation:

```json
{
  "run_id": "e5f6a7b8-c9d0-1234-ef01-234567890004",
  "proposal_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "decision_id": "c3d4e5f6-a7b8-9012-cdef-012345678902",
  "status": "success",
  "success": true,
  "changed_files": [
    {
      "path": "src/main.py",
      "change_type": "modified",
      "lines_added": 3,
      "lines_removed": 3
    },
    {
      "path": "src/utils.py",
      "change_type": "modified",
      "lines_added": 1,
      "lines_removed": 1
    }
  ],
  "diff_stat_excerpt": "2 files changed, 4 insertions(+), 4 deletions(-)",
  "validation": {
    "status": "passed",
    "commands_run": 1,
    "commands_passed": 1,
    "commands_failed": 0,
    "failure_excerpt": null,
    "duration_ms": 820
  },
  "branch_pushed": true,
  "branch_name": "auto/lint-fix-TASK-1042-e5f6a7b8",
  "pull_request_url": null,
  "failure_category": null,
  "failure_reason": null,
  "artifacts": [
    {
      "artifact_id": "f6a7b8c9-d0e1-2345-f012-345678900005",
      "artifact_type": "diff",
      "label": "final diff",
      "content": "--- a/src/main.py\n+++ b/src/main.py\n@@ ...",
      "uri": null,
      "size_bytes": 312,
      "produced_at": "2026-04-22T09:01:30Z"
    }
  ],
  "completed_at": "2026-04-22T09:01:52Z"
}
```

Failed run: validation did not pass:

```json
{
  "run_id": "b8c9d0e1-f2a3-4567-1234-678901200008",
  "proposal_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "decision_id": "d4e5f6a7-b8c9-0123-def0-123456789003",
  "status": "failed",
  "success": false,
  "changed_files": [
    {
      "path": "src/middleware/rate_limit.py",
      "change_type": "added",
      "lines_added": 87,
      "lines_removed": 0
    }
  ],
  "diff_stat_excerpt": "1 file changed, 87 insertions(+)",
  "validation": {
    "status": "failed",
    "commands_run": 2,
    "commands_passed": 1,
    "commands_failed": 1,
    "failure_excerpt": "FAILED tests/test_rate_limit.py::test_limit_exceeded - AssertionError",
    "duration_ms": 14200
  },
  "branch_pushed": false,
  "branch_name": "auto/feature-TASK-2001-b8c9d0e1",
  "pull_request_url": null,
  "failure_category": "validation_failed",
  "failure_reason": "pytest: 1 test failed (tests/test_rate_limit.py)",
  "artifacts": [],
  "completed_at": "2026-04-22T14:37:44Z"
}
```

---

## End-to-end flow trace

The following shows how IDs chain across the full lifecycle for a single task:

```
ControlPlane emits:
  TaskProposal
    proposal_id: "a1b2c3d4-..."
    task_id:     "TASK-1042"

SwitchBoard emits:
  LaneDecision
    decision_id:  "c3d4e5f6-..."
    proposal_id:  "a1b2c3d4-..."   ← ties back to TaskProposal

Lane runner creates:
  ExecutionRequest
    run_id:       "e5f6a7b8-..."
    proposal_id:  "a1b2c3d4-..."   ← ties back to TaskProposal
    decision_id:  "c3d4e5f6-..."   ← ties back to LaneDecision

Backend adapter produces:
  RunTelemetry
    run_id:       "e5f6a7b8-..."   ← ties back to ExecutionRequest

  ExecutionResult
    run_id:       "e5f6a7b8-..."   ← ties back to ExecutionRequest
    proposal_id:  "a1b2c3d4-..."   ← original task chain
    decision_id:  "c3d4e5f6-..."   ← routing chain
```

Every model in the chain carries the `run_id`. Every model except RunTelemetry
carries `proposal_id`. This makes the full chain traceable from a single ID at
any point in the pipeline.
