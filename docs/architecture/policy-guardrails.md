# Policy and Guardrails (Phase 12)

## Purpose

The policy layer is the system's explicit enforcement boundary. It constrains what autonomous execution may do, gates high-risk or sensitive work behind human review, and blocks actions that are unconditionally unsafe regardless of task goal or routing choice.

Policy and guardrails are first-class system concerns. They do not live inside a single backend or shell. They evaluate canonical contract types (TaskProposal, LaneDecision) and return an inspectable decision (PolicyDecision) that any caller can act on.

---

## Architecture Position

```
ControlPlane
  └─ planning/    ← produces TaskProposal
  └─ routing/     ← produces LaneDecision
  └─ policy/      ← evaluates (proposal, decision) → PolicyDecision
                     ↑ sits between planning/routing and execution
SwitchBoard
  └─ lane runners ← only proceed if PolicyDecision.is_allowed or gates pass
```

The engine is stateless. It holds a `PolicyConfig` and evaluates proposals on demand. Nothing in the engine is backend-specific or shell-specific.

---

## Core Types

### Config models (mutable dataclasses)

| Type | Purpose |
|------|---------|
| `PolicyConfig` | Collection of `RepoPolicy` entries + optional default |
| `RepoPolicy` | Full policy for one repo (or `*` wildcard catch-all) |
| `PathPolicy` | Rules for path-level access control |
| `PathScopeRule` | One path pattern → access mode mapping |
| `BranchGuardrail` | Branch/PR flow requirements |
| `ToolGuardrail` | Network mode + destructive action restrictions |
| `ValidationRequirement` | Which validation profile is required at which risk level |
| `ReviewRequirement` | When human review is required |

### Decision models (frozen Pydantic)

| Type | Purpose |
|------|---------|
| `PolicyDecision` | Inspectable evaluation result |
| `PolicyStatus` | `ALLOW` / `ALLOW_WITH_WARNINGS` / `REQUIRE_REVIEW` / `BLOCK` |
| `PolicyViolation` | Specific rule that was violated (blocking or non-blocking) |
| `PolicyWarning` | Non-blocking concern |
| `PolicyExplanation` | Human-readable summary of a decision |

---

## PolicyEngine

```python
engine = PolicyEngine.from_defaults()
decision = engine.evaluate(proposal, lane_decision)

if decision.is_blocked:
    # stop execution
elif decision.requires_review:
    # gate on human approval
elif decision.is_allowed:
    # proceed (check for warnings if relevant)
```

**Evaluation order:**

1. Repo enabled check (short-circuits if disabled)
2. Task type allow/block list
3. Routing constraint check (local_only label vs remote lane)
4. Path restriction check
5. Branch guardrail check
6. Tool guardrail check (network mode, destructive actions)
7. Validation requirement check
8. Review requirement check
9. Aggregate → determine PolicyStatus

**Status determination:**
- Any blocking violation → `BLOCK`
- Non-blocking violations only (review gates) → `REQUIRE_REVIEW`
- Warnings only → `ALLOW_WITH_WARNINGS`
- Clean → `ALLOW`

---

## Policy Dimensions

### 1. Repo scope

Each `RepoPolicy` is keyed by `repo_key`. A `*` wildcard entry acts as fallback. When `enabled=False`, all work for that repo is immediately blocked.

Task types may be allowed or blocked explicitly:
- `allowed_task_types`: only listed types pass
- `blocked_task_types`: listed types are always blocked

### 2. Routing constraints

If a proposal carries the `local_only` or `no_remote` label, the routing decision must select a local lane (`aider_local`). A mismatch (remote lane selected) produces a blocking `routing.local_only_violated` violation.

### 3. Path restrictions

`PathPolicy.rules` is evaluated in order. The first matching `PathScopeRule` wins. Rules support fnmatch glob patterns.

Access modes:
- `allow` — permitted
- `read_only` — non-blocking violation (review required)
- `review_required` — non-blocking violation (review required)
- `block` — blocking violation

If no rule matches, `PathPolicy.default_mode` applies (`allow` / `block` / `review_required`).

### 4. Branch guardrail

- `allow_direct_commit=False` + empty `branch_prefix` → warning
- `allowed_base_branches` — blocking violation if base branch not in list
- `require_pr=True` + `open_pr=False` → non-blocking violation (review)

### 5. Tool guardrail

Network modes:
- `allowed` — any lane permitted
- `local_only` — remote lanes blocked (blocking violation)
- `blocked` — all execution blocked (blocking violation)

Destructive actions: if `allow_destructive_actions=False` and the proposal carries a label in `{rm_rf, drop_table, force_push, destructive}`, a blocking violation is raised.

### 6. Validation requirements

Each `ValidationRequirement` targets a set of risk levels (and optionally task types). If validation commands are unavailable:
- `block_if_unavailable=True` → blocking violation
- `block_if_unavailable=False` → warning

### 7. Human review requirements

- `blocked_without_human=True` → always blocking (autonomous execution forbidden)
- `autonomous_allowed=False` → non-blocking review violation
- Risk level or task type in review lists → non-blocking review violation
- `review_required` label on proposal → non-blocking review violation

---

## Default Policy

`DEFAULT_REPO_POLICY` applies to all repos via `repo_key="*"`. Conservative posture:

| Dimension | Default |
|-----------|---------|
| Branch | No direct commit; branch required; pattern `auto/*`; no PR required |
| Network | Allowed |
| Destructive | Blocked |
| High-risk | Review required + `strict` validation required (blocks if unavailable) |
| Medium-risk | `standard` validation recommended (warns if unavailable) |
| Feature/refactor | Review required |
| SSH keys | Blocked (`**/.ssh/**`, `**/.gnupg/**`) |
| Env files | Review required (`.env*`, `*.env`) |
| Migrations | Review required (`**/migrations/**`) |
| Workflows | Review required (`.github/workflows/**`) |
| Dockerfiles | Review required (`Dockerfile*`, `docker-compose*.yml`) |

---

## Validation

`validate_config(config) -> list[str]` returns human-readable error strings. An empty list means the config is logically consistent. It catches:

- Invalid enum values (access_mode, network_mode, risk_profile, risk_level)
- Contradictory flags (allow_direct_commit + require_branch; blocked_without_human + autonomous_allowed)
- Empty required fields (repo_key, path_pattern, required_profile)
- Duplicate repo_keys

---

## Explanation

`explain(decision) -> PolicyExplanation` translates a `PolicyDecision` into human-readable reasoning:

- `summary` — one-line status with first violation message
- `key_rules_applied` — list of rule IDs from violations and warnings
- `review_reasoning` — why review is required (or not)
- `validation_reasoning` — validation profile in effect
- `scope_reasoning` — effective path scope with violations
- `routing_reasoning` — routing compatibility explanation

---

## File Map

```
src/control_plane/policy/
  __init__.py        — public API
  models.py          — all typed models (config + decision)
  defaults.py        — DEFAULT_REPO_POLICY, DEFAULT_POLICY_CONFIG
  engine.py          — PolicyEngine, evaluate(), sub-checks
  validate.py        — validate_config()
  explain.py         — explain()

tests/unit/policy/
  conftest.py        — make_proposal(), make_decision(), make_repo_policy()
  test_models.py     — model construction, frozen/mutable, helper properties
  test_engine.py     — ALLOW / ALLOW_WITH_WARNINGS / REQUIRE_REVIEW / BLOCK paths
  test_defaults.py   — DEFAULT_REPO_POLICY structure and posture
  test_validate.py   — valid configs, contradictions, duplicate keys
  test_explain.py    — summary text, key_rules_applied, reasoning fields

tests/fixtures/policy/
  low_risk_bounded.json
  high_risk_sensitive_path.json
  local_only_blocked.json
  branch_rule_pr_required.json
  destructive_tool_blocked.json
```
