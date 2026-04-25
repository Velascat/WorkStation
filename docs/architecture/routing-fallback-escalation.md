# Routing Fallback and Escalation Architecture

This document describes the fallback and escalation policy in SwitchBoard — how routing turns from a single-choice selector into a controlled decision system with explicit alternative paths.

---

## Why this exists

Without this layer, SwitchBoard can select a primary lane and backend but has no disciplined answer to questions like:

- What if `aider_local` is unavailable right now?
- What if a task is local-preferred but too risky for the local lane?
- What if `kodo` is selected but the task complexity calls for workflow orchestration?
- What is the next acceptable path if the primary is blocked?

Without explicit policy, those answers become ad hoc code in callers, backend-specific hacks, or silent failures.

This layer makes fallback and escalation **first-class policy outputs**.

---

## Concepts

### Primary route

The first-choice lane and backend for a task. Selected by the existing `LaneSelector.select()` logic.

### Fallback route

A lower-preference alternative used when the primary route is **unavailable or fails** at execution time.

Fallbacks are cheaper or simpler paths. Example: local task primary is `aider_local`/`direct_local`; fallback is `claude_cli`/`kodo` if local execution is unavailable.

Fallbacks are **not** used automatically. The execution layer decides whether and when to act on them.

### Escalation route

A higher-capability alternative used when the primary route is **likely insufficient** — the task is more complex, higher-risk, or needs stronger validation discipline than the primary provides.

Escalations are **policy-recommended**, not automatic. Example: `claude_cli`/`kodo` primary for a high-risk task escalates to `claude_cli`/`archon_then_kodo` for structured workflow discipline.

Escalation to `archon_then_kodo` requires positive justification (task shape or risk level). It is not offered merely because a higher tier exists.

### Blocked candidate

A route that policy knows about but that is **explicitly prohibited** by a constraint label or policy exclusion. Blocked candidates are visible in the routing plan with their reasons, so callers can explain why a seemingly attractive path was not offered.

Two distinct block reasons:
- `BLOCKED_BY_CONSTRAINT`: a proposal label (`local_only`, `no_remote`) hard-blocks this path. Do not use regardless of circumstances.
- `BLOCKED_BY_POLICY`: `excluded_backends` config excludes this backend. Do not use unless policy changes.

These are meaningfully different from each other and from simply "not warranted."

---

## Routing flow

```
TaskProposal
  │
  ▼
LaneSelector._evaluate_rules()
  │
  ▼
Primary RouteCandidate (lane, backend, confidence, cost_class, capability_class)
  │
  ├── FallbackPolicyEngine.evaluate()
  │     └── AlternativeRoute[role="fallback"] filtered by:
  │           • from_lanes / from_backends (primary route relevance)
  │           • blocked_by_labels (constraint enforcement)
  │           • excluded_backends (policy enforcement)
  │           • applies_when conditions (proposal attributes)
  │     → FallbackPlan + blocked list
  │
  ├── EscalationPolicyEngine.evaluate()
  │     └── AlternativeRoute[role="escalation"] filtered by same criteria
  │     → EscalationPlan + blocked list
  │
  ▼
RoutingPlan
  ├── primary
  ├── fallbacks (eligible fallback candidates)
  ├── escalations (eligible escalation candidates)
  ├── blocked_candidates (constraint + policy blocks, with reasons)
  ├── policy_summary
  ├── primary_reason / fallback_reasoning / escalation_reasoning / blocked_reasoning
```

---

## Key types

### `RouteCandidate`

A lane/backend pair with routing context:

| Field | Purpose |
|-------|---------|
| `lane` | LaneName value |
| `backend` | BackendName or extended backend |
| `priority` | Ordering among candidates of the same role |
| `reason` | Why this candidate exists or was blocked |
| `eligibility_status` | ELIGIBLE / BLOCKED_BY_CONSTRAINT / BLOCKED_BY_POLICY / UNSUPPORTED / DEPRIORITIZED |
| `confidence` | Policy confidence (0.0–1.0) |
| `estimated_cost_class` | CostClass: low / medium / high |
| `estimated_capability_class` | CapabilityClass: basic / enhanced / premium / workflow |

### `CostClass`

| Value | Meaning |
|-------|---------|
| `low` | Local execution, zero marginal cost |
| `medium` | Remote model execution, modest API cost |
| `high` | Workflow orchestration or premium tier |

### `CapabilityClass`

| Value | Meaning |
|-------|---------|
| `basic` | Lightweight local execution |
| `enhanced` | Remote model, good reasoning, low overhead |
| `premium` | Highest-tier model, best reasoning quality |
| `workflow` | Structured multi-step workflow orchestration |

### `AlternativeRoute` (policy definition)

Defines a potential fallback or escalation in the policy:

| Field | Purpose |
|-------|---------|
| `role` | "fallback" or "escalation" |
| `from_lanes` | Only relevant when primary lane is in this list |
| `from_backends` | Only relevant when primary backend is in this list |
| `applies_when` | Proposal attribute conditions (same semantics as LaneRule.when) |
| `blocked_by_labels` | Proposal labels that hard-block this path |
| `cost_class` / `capability_class` | For explanation |
| `confidence` | Policy confidence when this alternative is eligible |
| `reason` | Human-readable explanation |

---

## Constraint enforcement

Constraints are enforced visibly, not silently:

1. A proposal with `local_only` label → all remote alternatives have `blocked_by_labels=["local_only"]` → they appear in `blocked_candidates` with `BLOCKED_BY_CONSTRAINT` status and the blocking label named.
2. A policy with `excluded_backends=["archon_then_kodo"]` → Archon alternatives appear in `blocked_candidates` with `BLOCKED_BY_POLICY`.
3. A path that simply isn't warranted (e.g. escalation for low-risk task) → does not appear at all. Not warranted is distinct from blocked.

**The distinction matters:** execution layers need to know whether a path is "never use this" vs "don't use this first" vs "not applicable here."

---

## Ownership boundary

SwitchBoard owns:
- Deciding primary route preference
- Defining acceptable alternative routes
- Evaluating constraint blocks and policy exclusions
- Producing inspectable routing explanations

Backend adapters own:
- Support/suitability checks specific to that backend
- Execution-time failure details

Execution and orchestration layers own:
- Whether and when to actually use a fallback
- Retry orchestration
- Carrying context between attempts

**SwitchBoard does not execute backends. It does not run retries. It does not chain runs.**

---

## API entry points

```python
from switchboard.lane.engine import LaneSelector
from switchboard.lane.planner import DecisionPlanner

# Simple primary route
selector = LaneSelector()
decision = selector.select(proposal)      # → LaneDecision

# Full routing plan with alternatives
plan = selector.plan_routes(proposal)     # → RoutingPlan
# or
planner = DecisionPlanner()
plan = planner.plan(proposal)             # → RoutingPlan

print(plan.primary.lane, plan.primary.backend)
print(plan.fallbacks.candidates)
print(plan.escalations.candidates)
print(plan.blocked_candidates)
print(plan.policy_summary)
```

---

## Default policy routing tendencies

### Stay local when safe

```
proposal: local_only label → force aider_local, ALL remote paths blocked
proposal: low-risk local task → aider_local primary, remote fallback available (if not local_only)
```

### Escalate when risk demands it

```
local primary + medium/high risk → escalation to claude_cli/kodo available
kodo primary + high risk → escalation to archon_then_kodo available
```

### Workflow only when warranted

```
kodo primary + refactor/feature task type → archon_then_kodo escalation
kodo primary + high risk → archon_then_kodo escalation
refactor/feature + medium/high risk → archon_then_kodo as PRIMARY (direct, via premium_structured rule)
```

Note: if a task is structured enough to need workflow, the default policy often routes it to `archon_then_kodo` as the primary rather than offering it as an escalation. Escalation is for tasks that landed on kodo first but could benefit from workflow discipline.

---

## Policy tuning

Add or modify `alternative_routes` in `LaneRoutingPolicy` to change fallback/escalation behavior:

```python
from switchboard.lane.policy import AlternativeRoute, LaneRoutingPolicy

policy = LaneRoutingPolicy(
    rules=[...],
    alternative_routes=[
        AlternativeRoute(
            name="my_fallback",
            lane="claude_cli",
            backend="kodo",
            role="fallback",
            from_lanes=["aider_local"],
            blocked_by_labels=["local_only"],
            reason="Remote fallback for local-first tasks.",
            confidence=0.85,
        ),
    ],
)
```

Key policy dimensions you can tune:
- `from_lanes` / `from_backends` — which primaries this alternative is relevant for
- `applies_when` — proposal attribute conditions
- `blocked_by_labels` — constraint labels that hard-block this path
- `priority` — preference ordering among alternatives of the same role
- `confidence` — policy confidence in this alternative
