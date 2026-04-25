# OperationsCenter Routing Examples

Concrete examples showing how planning context flows through the proposal
builder and SwitchBoard routing to produce a `ProposalDecisionBundle`.

---

## Example 1 — Lint fix, low risk → aider_local

**PlanningContext:**

```python
PlanningContext(
    goal_text="Fix all ruff lint errors in src/. Do not change logic.",
    task_type="lint_fix",
    repo_key="api-service",
    clone_url="https://github.com/org/api-service.git",
    base_branch="main",
    risk_level="low",
    priority="normal",
    allowed_paths=["src/**"],
    validation_commands=["ruff check src/"],
    timeout_seconds=300,
)
```

**TaskProposal (after build_proposal):**

```json
{
  "proposal_id": "a1b2c3d4-...",
  "task_id": "auto-lint-fix-e3b0c442",
  "task_type": "lint_fix",
  "execution_mode": "goal",
  "goal_text": "Fix all ruff lint errors in src/. Do not change logic.",
  "risk_level": "low",
  "priority": "normal",
  "target": {
    "repo_key": "api-service",
    "clone_url": "https://github.com/org/api-service.git",
    "base_branch": "main",
    "allowed_paths": ["src/**"]
  },
  "constraints": {
    "timeout_seconds": 300,
    "allowed_paths": ["src/**"],
    "require_clean_validation": true
  },
  "validation_profile": {
    "profile_name": "default",
    "commands": ["ruff check src/"]
  },
  "labels": []
}
```

**LaneDecision (from SwitchBoard):**

```json
{
  "decision_id": "c3d4e5f6-...",
  "proposal_id": "a1b2c3d4-...",
  "selected_lane": "aider_local",
  "selected_backend": "kodo",
  "confidence": 0.95,
  "policy_rule_matched": "local_low_risk"
}
```

**run_summary:**
```
proposal=a1b2c3d4 task=auto-lint-fix-e3b0c442 lane=aider_local backend=kodo rule=local_low_risk
```

---

## Example 2 — Bug fix, medium risk → claude_cli

**PlanningContext:**

```python
PlanningContext(
    goal_text="Fix the race condition in the cache invalidation path.",
    task_type="bug_fix",
    repo_key="cache-service",
    clone_url="https://github.com/org/cache-service.git",
    risk_level="medium",
    priority="high",
    task_id="TASK-2041",
    project_id="proj-cache",
    proposer="operations-center",
)
```

**LaneDecision:**

```json
{
  "selected_lane": "claude_cli",
  "selected_backend": "kodo",
  "confidence": 0.90,
  "policy_rule_matched": "medium_implementation"
}
```

---

## Example 3 — Refactor, high risk → claude_cli + archon_then_kodo

**PlanningContext:**

```python
PlanningContext(
    goal_text="Refactor the authentication module to use the new session API.",
    task_type="refactor",
    repo_key="auth-service",
    clone_url="https://github.com/org/auth-service.git",
    risk_level="high",
    priority="normal",
    max_changed_files=30,
    timeout_seconds=600,
)
```

**LaneDecision:**

```json
{
  "selected_lane": "claude_cli",
  "selected_backend": "archon_then_kodo",
  "confidence": 0.85,
  "policy_rule_matched": "premium_structured"
}
```

---

## Example 4 — local_only label forces aider_local

**PlanningContext:**

```python
PlanningContext(
    goal_text="Update CHANGELOG with recent commits.",
    task_type="documentation",
    repo_key="api-service",
    clone_url="https://github.com/org/api-service.git",
    risk_level="high",        # would normally escalate
    labels=["local_only"],    # overrides all other factors
)
```

**LaneDecision:**

```json
{
  "selected_lane": "aider_local",
  "selected_backend": "direct_local",
  "confidence": 1.0,
  "policy_rule_matched": "force_local_only"
}
```

`local_only` in labels is the hard override. Risk level is ignored.

---

## Example 5 — Custom task_id and trace_notes

```python
ctx = PlanningContext(
    goal_text="Write unit tests for the payment processor module.",
    task_type="test_write",
    repo_key="payments",
    clone_url="https://github.com/org/payments.git",
    task_id="TASK-3099",          # explicit; not auto-derived
    project_id="proj-payments",
    risk_level="low",
    validation_commands=["pytest tests/unit/payment/"],
)

service = PlanningService.default()
bundle = service.plan(ctx, trace_notes="triggered by Plane webhook")

print(bundle.proposal.task_id)    # TASK-3099
print(bundle.trace_notes)         # triggered by Plane webhook
print(bundle.run_summary)         # proposal=... task=TASK-3099 lane=... ...
```

---

## Example 6 — Validation context fails gracefully

```python
ctx = PlanningContext(
    goal_text="",             # invalid — will raise
    task_type="lint_fix",
    repo_key="svc",
    clone_url="https://github.com/org/svc.git",
)

try:
    service.plan(ctx)
except ValueError as e:
    print(e)
    # PlanningContext validation failed: goal_text must not be empty
```

---

## Example 7 — Using StubLaneRoutingClient in a test

```python
from operations_center.contracts.enums import BackendName, LaneName
from operations_center.contracts.routing import LaneDecision
from operations_center.planning.models import PlanningContext
from operations_center.routing.client import StubLaneRoutingClient
from operations_center.routing.service import PlanningService

stub = StubLaneRoutingClient(
    LaneDecision(
        proposal_id="",
        selected_lane=LaneName.CLAUDE_CLI,
        selected_backend=BackendName.KODO,
        confidence=1.0,
    )
)
service = PlanningService.with_client(stub)

ctx = PlanningContext(
    goal_text="Fix all lint errors",
    task_type="lint_fix",
    repo_key="svc",
    clone_url="https://github.com/org/svc.git",
)
bundle = service.plan(ctx)
assert bundle.decision.selected_lane == LaneName.CLAUDE_CLI
```

---

## Example 8 — Full pipeline (proposal → execution request stub)

```python
from operations_center.planning.models import PlanningContext
from operations_center.routing.service import PlanningService

ctx = PlanningContext(
    goal_text="Upgrade all dependencies to their latest patch versions.",
    task_type="dependency_update",
    repo_key="infra",
    clone_url="https://github.com/org/infra.git",
    base_branch="main",
    risk_level="medium",
    priority="normal",
    task_id="TASK-4200",
    validation_commands=["pip check"],
    timeout_seconds=900,
    push_on_success=True,
    open_pr=True,
)

service = PlanningService.default()
bundle = service.plan(ctx)

# Downstream: construct ExecutionRequest from bundle
from operations_center.contracts.execution import ExecutionRequest
from pathlib import Path

request = ExecutionRequest(
    proposal_id=bundle.proposal.proposal_id,
    decision_id=bundle.decision.decision_id,
    goal_text=bundle.proposal.goal_text,
    constraints_text=bundle.proposal.constraints_text,
    repo_key=bundle.proposal.target.repo_key,
    clone_url=bundle.proposal.target.clone_url,
    base_branch=bundle.proposal.target.base_branch,
    task_branch="auto/dep-update-TASK-4200",
    workspace_path=Path("/tmp/ws/infra-TASK-4200"),
    timeout_seconds=bundle.proposal.constraints.timeout_seconds,
    validation_commands=list(bundle.proposal.validation_profile.commands),
)

# → pass to KodoBackendAdapter.execute(request)
```
