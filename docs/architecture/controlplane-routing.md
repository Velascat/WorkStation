# ControlPlane Routing Architecture

How ControlPlane shapes a `TaskProposal` from planning context, routes it
through SwitchBoard, and bundles the result for downstream execution.

---

## Overview

ControlPlane's planning and routing pipeline has three stages:

```
PlanningContext
    │
    ▼ ProposalBuilder
TaskProposal
    │
    ▼ LaneRoutingClient → SwitchBoard (LaneSelector)
LaneDecision
    │
    ▼ PlanningService bundles both
ProposalDecisionBundle
```

Each stage is a pure translation with no side effects. The bundle is
the hand-off point for the execution layer (lane runner + backend adapter).

---

## PlanningContext

`PlanningContext` is a frozen dataclass that carries raw task intent before it
is translated into canonical types. It is ControlPlane-internal and never
crosses a repo boundary.

```python
@dataclass(frozen=True)
class PlanningContext:
    # What
    goal_text: str
    task_type: str          # "lint_fix", "bug_fix", etc.
    execution_mode: str     # "goal" (default)

    # Where
    repo_key: str
    clone_url: str
    base_branch: str        # "main" (default)
    allowed_paths: list[str]

    # Risk and scheduling
    risk_level: str         # "low" / "medium" / "high"
    priority: str           # "low" / "normal" / "high" / "critical"
    max_changed_files: Optional[int]
    timeout_seconds: int    # 300 (default)

    # Validation
    validation_profile_name: str
    validation_commands: list[str]
    require_clean_validation: bool

    # Tracing
    task_id: str
    project_id: str
    constraints_text: Optional[str]
    labels: list[str]
    proposer: str           # "control-plane" (default)

    # Branch policy
    push_on_success: bool   # True (default)
    open_pr: bool           # False (default)
```

---

## ProposalBuilder

`build_proposal(context: PlanningContext) -> TaskProposal`

The proposal builder is a pure function. It:

1. Validates that `goal_text`, `repo_key`, and `clone_url` are non-empty.
2. Maps `str` field values to canonical enum types, falling back gracefully:
   - Unknown `task_type` → `TaskType.UNKNOWN`
   - Unknown `execution_mode` → `ExecutionMode.GOAL`
   - Unknown `risk_level` → `RiskLevel.LOW`
   - Unknown `priority` → `Priority.NORMAL`
3. Assembles `TaskTarget`, `ExecutionConstraints`, `ValidationProfile`,
   `BranchPolicy` from context fields.
4. Derives a stable `task_id` if none is provided:
   `auto-{task_type_slug[:20]}-{sha1(goal_text)[:8]}`

No backend knowledge. No routing logic. No external calls.

```python
from control_plane.planning import build_proposal, PlanningContext

ctx = PlanningContext(
    goal_text="Fix all ruff errors in src/",
    task_type="lint_fix",
    repo_key="api-service",
    clone_url="https://github.com/org/api-service.git",
)
proposal = build_proposal(ctx)
# → TaskProposal (canonical, frozen)
```

---

## LaneRoutingClient

`LaneRoutingClient` is a `Protocol` — a structural interface that isolates how
SwitchBoard is called. ControlPlane's service layer calls only:

```python
decision: LaneDecision = client.select_lane(proposal)
```

### Implementations

| Class | Mechanism | When to use |
|---|---|---|
| `HttpLaneRoutingClient` | HTTP call to SwitchBoard `/route` | Default; production + CI |
| `LocalLaneRoutingClient` | In-process `LaneSelector` import | Compatibility-only local/dev use |
| `StubLaneRoutingClient` | Returns a fixed `LaneDecision` | Unit tests |

`HttpLaneRoutingClient` is the supported default:

```bash
export CONTROL_PLANE_SWITCHBOARD_URL=http://localhost:20401
```

```python
from control_plane.routing import HttpLaneRoutingClient

client = HttpLaneRoutingClient.from_env()
decision = client.select_lane(proposal)
```

`StubLaneRoutingClient` injects a fixed decision — no SwitchBoard dependency:

```python
from control_plane.routing import StubLaneRoutingClient
from control_plane.contracts.routing import LaneDecision
from control_plane.contracts.enums import LaneName, BackendName

stub = StubLaneRoutingClient(
    LaneDecision(
        proposal_id="",
        selected_lane=LaneName.CLAUDE_CLI,
        selected_backend=BackendName.KODO,
    )
)
```

---

## PlanningService

`PlanningService` orchestrates the full pipeline in one call:

```python
service = PlanningService.default()
bundle = service.plan(context)
```

`plan()` is equivalent to:

```python
proposal  = build_proposal(context)
decision  = routing_client.select_lane(proposal)
bundle    = ProposalDecisionBundle(proposal=proposal, decision=decision, context=context)
```

### Constructors

```python
# Default: HttpLaneRoutingClient against the SwitchBoard service boundary
service = PlanningService.default()

# Inject any LaneRoutingClient
service = PlanningService.with_client(my_client)
```

### trace_notes

Pass a string to tag the bundle for tracing:

```python
bundle = service.plan(context, trace_notes="cron-job:nightly-lint")
```

---

## ProposalDecisionBundle

The bundle is the hand-off object from planning to execution:

```python
@dataclass
class ProposalDecisionBundle:
    proposal: TaskProposal    # canonical proposal
    decision: LaneDecision    # SwitchBoard's routing choice
    context: PlanningContext  # original planning context (optional; for audit)
    bundled_at: datetime
    trace_notes: str

    @property
    def run_summary(self) -> str:
        # "proposal=<id[:8]> task=<task_id> lane=<lane> backend=<backend> rule=<rule>"
```

The execution layer uses `bundle.decision.selected_lane` and
`bundle.decision.selected_backend` to choose and invoke the right adapter.

---

## Ownership boundaries

| Concern | Owner |
|---|---|
| Planning context → TaskProposal | `ControlPlane: planning/proposal_builder.py` |
| Routing policy and lane selection | `SwitchBoard: lane/engine.py` |
| Calling SwitchBoard | `ControlPlane: routing/client.py` |
| Bundling proposal + decision | `ControlPlane: routing/service.py` |
| Executing the task | Lane runner (downstream, outside this scope) |

ControlPlane never embeds routing logic. All policy lives in SwitchBoard.

---

## Module layout

```
src/control_plane/
  planning/
    __init__.py          — public API
    models.py            — PlanningContext, ProposalBuildResult, ProposalDecisionBundle
    proposal_builder.py  — build_proposal(), build_proposal_with_result()
  routing/
    __init__.py          — public API
    client.py            — LaneRoutingClient protocol, HttpLaneRoutingClient, LocalLaneRoutingClient, StubLaneRoutingClient
    service.py           — PlanningService
```

---

## See also

- [contracts.md](contracts.md) — TaskProposal, LaneDecision canonical types
- [routing.md](../../../SwitchBoard/docs/routing.md) — SwitchBoard policy and LaneSelector
- [kodo-adapter.md](kodo-adapter.md) — how the execution layer consumes ExecutionRequest
