# Routing Fallback and Escalation — Usage Examples

Concrete examples for Phase 9 fallback/escalation policy. All examples use `DecisionPlanner` or `LaneSelector.plan_routes()`.

---

## 1. Safe local task — no remote escalation allowed

```python
from control_plane.contracts import TaskProposal
from control_plane.contracts.enums import TaskType, RiskLevel
from switchboard.lane.planner import DecisionPlanner

proposal = TaskProposal(
    task_id="TASK-101",
    project_id="proj-1",
    task_type=TaskType.LINT_FIX,
    risk_level=RiskLevel.LOW,
    labels=["local_only"],     # ← explicit constraint
    ...
)

plan = DecisionPlanner().plan(proposal)

print(plan.primary.lane)                     # "aider_local"
print(plan.primary.backend)                  # "direct_local"
print(plan.fallbacks.candidates)             # []  — all remote paths blocked
print(plan.blocked_candidates[0].reason)     # "Fallback route blocked by constraint label(s): local_only"
print(plan.blocked_candidates[0].eligibility_status)  # "blocked_by_constraint"
print(plan.blocked_reasoning)                # "Constraint-blocked: claude_cli/kodo"
```

---

## 2. Local-preferred task with remote fallback allowed

```python
proposal = TaskProposal(
    task_type=TaskType.LINT_FIX,
    risk_level=RiskLevel.LOW,
    labels=[],                 # ← no local_only constraint
    ...
)

plan = DecisionPlanner().plan(proposal)

print(plan.primary.lane)                     # "aider_local"
print(plan.primary.backend)                  # "direct_local"
print(plan.fallbacks.candidates[0].lane)     # "claude_cli"
print(plan.fallbacks.candidates[0].backend)  # "kodo"
print(plan.fallbacks.reasoning)              # "1 fallback route(s) available. First: claude_cli/kodo."
print(plan.escalations.candidates)           # [] — low risk, no escalation warranted
```

---

## 3. Complex task that routes directly to workflow primary

Refactor and feature tasks with medium/high risk are routed to `archon_then_kodo` as primary — no escalation needed.

```python
proposal = TaskProposal(
    task_type=TaskType.REFACTOR,
    risk_level=RiskLevel.MEDIUM,
    labels=[],
    ...
)

plan = DecisionPlanner().plan(proposal)

print(plan.primary.lane)                            # "claude_cli"
print(plan.primary.backend)                         # "archon_then_kodo"
print(plan.primary.estimated_capability_class)      # "workflow"
print(plan.escalations.candidates)                  # [] — already at workflow tier
```

---

## 4. High-risk bug fix that lands on kodo with workflow escalation

```python
proposal = TaskProposal(
    task_type=TaskType.BUG_FIX,
    risk_level=RiskLevel.HIGH,
    labels=[],
    ...
)

plan = DecisionPlanner().plan(proposal)

print(plan.primary.lane)                            # "claude_cli"
print(plan.primary.backend)                         # "kodo"
print(plan.escalations.candidates[0].backend)       # "archon_then_kodo"
print(plan.escalations.candidates[0].reason)        # "High-risk change benefits from structured workflow..."
print(plan.policy_summary)                          # "primary=claude_cli/kodo; escalations=1"
```

---

## 5. Explicit constraints block all remote alternatives

```python
proposal = TaskProposal(
    task_type=TaskType.REFACTOR,
    risk_level=RiskLevel.HIGH,
    labels=["local_only"],
    ...
)

plan = DecisionPlanner().plan(proposal)

# Primary is still local (force_local_only rule wins)
print(plan.primary.lane)                     # "aider_local"

# All remote fallbacks and escalations are blocked
remote_fallbacks = [c for c in plan.fallbacks.candidates if c.lane != "aider_local"]
remote_escalations = [c for c in plan.escalations.candidates if c.lane != "aider_local"]
print(remote_fallbacks)                      # []
print(remote_escalations)                    # []

# Blocked candidates are recorded with reasons
print(len(plan.blocked_candidates) > 0)      # True
for b in plan.blocked_candidates:
    print(b.eligibility_status, b.reason)
    # "blocked_by_constraint", "... blocked by constraint label(s): local_only"
```

---

## 6. Using `LaneSelector.plan_routes()` vs `select()`

```python
from switchboard.lane.engine import LaneSelector

selector = LaneSelector()
proposal = ...

# Simple primary route only (Phase 4 behavior, unchanged)
decision = selector.select(proposal)
# decision.selected_lane, decision.selected_backend

# Full routing plan with alternatives (Phase 9)
plan = selector.plan_routes(proposal)
# plan.primary, plan.fallbacks, plan.escalations, plan.blocked_candidates

# Primary route is consistent between both
assert plan.primary.lane == decision.selected_lane.value
```

---

## 7. Custom policy with specific fallback/escalation rules

```python
from switchboard.lane.policy import AlternativeRoute, LaneRoutingPolicy, FallbackPolicy

policy = LaneRoutingPolicy(
    rules=[...],
    fallback=FallbackPolicy(lane="claude_cli", backend="kodo"),
    alternative_routes=[
        # Fallback: local → premium if local unavailable (blocked if local_only)
        AlternativeRoute(
            name="local_to_remote",
            lane="claude_cli",
            backend="kodo",
            role="fallback",
            from_lanes=["aider_local"],
            blocked_by_labels=["local_only", "no_remote"],
            confidence=0.85,
            reason="Premium lane available if local execution fails.",
        ),
        # Escalation: kodo → workflow for high risk (blocked if no_remote)
        AlternativeRoute(
            name="kodo_to_workflow",
            lane="claude_cli",
            backend="archon_then_kodo",
            role="escalation",
            from_backends=["kodo"],
            applies_when={"risk_level": "high"},
            blocked_by_labels=["no_remote"],
            confidence=0.88,
            reason="High risk warrants structured workflow orchestration.",
        ),
    ],
)

from switchboard.lane.planner import DecisionPlanner
planner = DecisionPlanner(policy=policy)
plan = planner.plan(proposal)
```

---

## 8. Interpreting the routing plan

```python
plan = DecisionPlanner().plan(proposal)

# Primary: always present, always ELIGIBLE
print(f"Route: {plan.primary.lane}/{plan.primary.backend}")
print(f"Cost: {plan.primary.estimated_cost_class}")       # low/medium/high
print(f"Capability: {plan.primary.estimated_capability_class}")  # basic/enhanced/premium/workflow
print(f"Confidence: {plan.primary.confidence:.0%}")

# Fallbacks: use if primary fails or is unavailable
if plan.fallbacks.candidates:
    first_fallback = plan.fallbacks.candidates[0]
    print(f"Fallback: {first_fallback.lane}/{first_fallback.backend}")
print(f"Fallback reasoning: {plan.fallback_reasoning}")

# Escalations: recommended if primary is likely insufficient
if plan.escalations.candidates:
    first_escalation = plan.escalations.candidates[0]
    print(f"Escalation: {first_escalation.lane}/{first_escalation.backend}")
    print(f"Reason: {first_escalation.reason}")
print(f"Escalation reasoning: {plan.escalation_reasoning}")

# Blocked: routes policy knows about but that are prohibited
for b in plan.blocked_candidates:
    print(f"BLOCKED {b.lane}/{b.backend}: {b.eligibility_status} — {b.reason}")
print(f"Blocked reasoning: {plan.blocked_reasoning}")
```

---

## 9. Eligibility status reference

| Status | Meaning for execution layers |
|--------|------------------------------|
| `ELIGIBLE` | Use this — conditions satisfied |
| `BLOCKED_BY_CONSTRAINT` | Never use this path for this proposal |
| `BLOCKED_BY_POLICY` | Do not use until policy exclusion is lifted |
| `UNSUPPORTED` | Backend cannot handle this request type |
| `DEPRIORITIZED` | Valid, but prefer higher-priority alternatives first |

---

## 10. Policy summary format

```
primary=claude_cli/kodo; fallbacks=1; escalations=2; blocked=1
```

Fields present only when non-zero:
- `fallbacks=N` — N eligible fallback candidates
- `escalations=N` — N eligible escalation candidates
- `blocked=N` — N blocked candidates
