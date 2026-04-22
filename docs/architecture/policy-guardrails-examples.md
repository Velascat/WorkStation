# Policy and Guardrails — Examples

## Example 1: Low-risk bounded task → ALLOW

```python
engine = PolicyEngine.from_defaults()

proposal = TaskProposal(
    task_id="TASK-001",
    task_type=TaskType.BUG_FIX,
    risk_level=RiskLevel.LOW,
    target=TaskTarget(
        repo_key="api-service",
        clone_url="git@github.com:org/api-service.git",
        base_branch="main",
        allowed_paths=["src/pagination.py", "tests/test_pagination.py"],
    ),
    ...
)

decision = engine.evaluate(proposal, lane_decision)
# decision.status == PolicyStatus.ALLOW
# decision.violations == []
# decision.warnings == []
```

---

## Example 2: High-risk feature touching migration path → REQUIRE_REVIEW

```python
proposal = TaskProposal(
    task_type=TaskType.FEATURE,
    risk_level=RiskLevel.HIGH,
    target=TaskTarget(
        repo_key="api-service",
        allowed_paths=["db/migrations/0010_add_roles.py", "src/models/role.py"],
    ),
    validation_profile=ValidationProfile(profile_name="strict", commands=["pytest"]),
    ...
)

decision = engine.evaluate(proposal, lane_decision)
# decision.status == PolicyStatus.REQUIRE_REVIEW
# Multiple non-blocking violations:
#   - path.review_required (migration path matched **/migrations/**)
#   - review.required (feature task type + high risk)
#   - validation.required_unavailable is NOT raised because commands=["pytest"]
```

---

## Example 3: local_only label with remote lane → BLOCK

```python
proposal = TaskProposal(
    task_type=TaskType.SIMPLE_EDIT,
    risk_level=RiskLevel.LOW,
    labels=["local_only"],
    target=TaskTarget(repo_key="docs-service", allowed_paths=["README.md"]),
    ...
)

lane_decision = LaneDecision(
    selected_lane=LaneName.CLAUDE_CLI,   # remote
    selected_backend=BackendName.OPENCLAW,
    ...
)

decision = engine.evaluate(proposal, lane_decision)
# decision.status == PolicyStatus.BLOCK
# decision.violations[0].rule_id == "routing.local_only_violated"
# decision.violations[0].blocking == True
```

---

## Example 4: Destructive label → BLOCK

```python
proposal = TaskProposal(
    task_type=TaskType.SIMPLE_EDIT,
    risk_level=RiskLevel.MEDIUM,
    labels=["rm_rf"],                    # ← triggers destructive check
    target=TaskTarget(repo_key="build-service", allowed_paths=["build/"]),
    ...
)

decision = engine.evaluate(proposal, lane_decision)
# decision.status == PolicyStatus.BLOCK
# decision.violations[0].rule_id == "tool.destructive_blocked"
```

---

## Example 5: PR required but not set → REQUIRE_REVIEW

```python
from control_plane.policy.models import BranchGuardrail

# Custom policy: PR required
policy = RepoPolicy(
    repo_key="auth-service",
    branch_guardrail=BranchGuardrail(require_pr=True),
    ...
)
engine = PolicyEngine.from_config(PolicyConfig(repo_policies=[policy]))

proposal = TaskProposal(
    task_type=TaskType.BUG_FIX,
    risk_level=RiskLevel.LOW,
    branch_policy=BranchPolicy(branch_prefix="auto/", open_pr=False),  # PR not set
    target=TaskTarget(repo_key="auth-service", allowed_paths=["src/auth/middleware.py"]),
    ...
)

decision = engine.evaluate(proposal, lane_decision)
# decision.status == PolicyStatus.REQUIRE_REVIEW
# decision.violations[0].rule_id == "branch.pr_required"
# decision.violations[0].blocking == False
```

---

## Example 6: Explanation generation

```python
explanation = explain(decision)

print(explanation.summary)
# "REVIEW REQUIRED: Human review required: risk='high', task_type='feature'"

print(explanation.key_rules_applied)
# ["path.review_required", "review.required"]

print(explanation.review_reasoning)
# "Human review required: risk='high', task_type='feature'"

print(explanation.scope_reasoning)
# "Effective scope: ['db/migrations/0010_add_roles.py', 'src/models/role.py']; Path 'db/migrations/0010_add_roles.py' requires human review (pattern: '**/migrations/**'; mode: 'review_required')"
```

---

## Example 7: Config validation catching contradictions

```python
from control_plane.policy.validate import validate_config

bad_policy = RepoPolicy(
    repo_key="bad-repo",
    branch_guardrail=BranchGuardrail(
        allow_direct_commit=True,   # contradicts require_branch
        require_branch=True,
    ),
    review_requirement=ReviewRequirement(
        blocked_without_human=True,  # contradicts autonomous_allowed
        autonomous_allowed=True,
    ),
)

errors = validate_config(PolicyConfig(repo_policies=[bad_policy]))
# errors == [
#   "repo_policies[0] (repo_key='bad-repo').branch_guardrail: allow_direct_commit=True contradicts require_branch=True",
#   "repo_policies[0] (repo_key='bad-repo').review_requirement: blocked_without_human=True contradicts autonomous_allowed=True",
# ]
```

---

## Example 8: Using from_config with a permissive override

```python
# Override: allow direct commit, no review required, destructive actions permitted
permissive_policy = RepoPolicy(
    repo_key="scratch-repo",
    enabled=True,
    branch_guardrail=BranchGuardrail(allow_direct_commit=True, require_branch=False),
    tool_guardrail=ToolGuardrail(allow_destructive_actions=True),
    review_requirement=ReviewRequirement(autonomous_allowed=True),
)
engine = PolicyEngine.from_config(
    PolicyConfig(repo_policies=[permissive_policy], default_policy=permissive_policy)
)

proposal = make_proposal(repo_key="scratch-repo", labels=["rm_rf"])
decision = engine.evaluate(proposal, remote_decision)
# decision.status == PolicyStatus.ALLOW
# Destructive actions allowed because allow_destructive_actions=True
```
