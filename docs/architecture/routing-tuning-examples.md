# Evidence-Driven Routing Tuning — Examples

## Example 1: Local lane performing well for bounded tasks

```python
from operations_center.tuning import StrategyTuningService

# records: 10 runs, kodo@aider_local, bug_fix, low risk, 90% success, fast latency
service = StrategyTuningService.default()
report = service.analyze(records)

print(report.comparison_summaries[0].reliability_class)  # ReliabilityClass.HIGH
print(report.comparison_summaries[0].latency_class)      # LatencyClass.FAST
print(report.comparison_summaries[0].evidence_strength)  # EvidenceStrength.MODERATE

# Findings
for f in report.findings:
    print(f.category, f.summary)
# reliability  kodo @ aider_local shows high reliability: 90% success rate across 10 runs.

# Recommendation
for p in report.recommendations:
    print(p.summary)
    print(p.affected_policy_area)
    print(p.requires_review)
# Consider increasing preference for kodo @ aider_local for bounded tasks.
# backend_preference
# True
```

---

## Example 2: Premium backend outperforming local for high-complexity tasks

```python
# records: 8 archon@claude_cli refactor tasks (87% success)
#        + 8 kodo@aider_local refactor tasks (12% success)

report = service.analyze(records)

by_backend = {s.backend: s for s in report.comparison_summaries}

print(by_backend["archon"].success_rate)       # 0.875
print(by_backend["archon"].reliability_class)  # ReliabilityClass.HIGH

print(by_backend["kodo"].success_rate)         # 0.125
print(by_backend["kodo"].reliability_class)    # ReliabilityClass.LOW

# Findings for kodo
kodo_findings = [f for f in report.findings if "kodo" in f.affected_backends]
for f in kodo_findings:
    print(f.summary)
# kodo @ aider_local shows low reliability: 12% success rate across 8 runs.

# Proposals from evidence
for p in report.recommendations:
    if "demoting" in p.summary:
        print(p.justification)
        print(p.evidence_strength)  # EvidenceStrength.MODERATE
        print(p.requires_review)    # True — always
```

---

## Example 3: OpenClaw backend with acceptable results but weak change evidence

```python
# records: 20 openclaw@claude_cli runs — high success but UNKNOWN changed-file status
# (backend did not report changed files for any run)

report = service.analyze(records)
s = report.comparison_summaries[0]

print(s.success_rate)            # 0.85
print(s.change_evidence_class)   # ChangeEvidenceClass.POOR
print(s.reliability_class)       # ReliabilityClass.HIGH

# Contradictory finding
for f in report.findings:
    if f.category == "contradictory":
        print(f.summary)
        print(f.notes)
# openclaw @ claude_cli is reliable by success rate but produces poor changed-file evidence...
# Consider restricting this backend to contexts where change enumeration is not a hard requirement.

# Proposal
for p in report.recommendations:
    print(p.summary)
    print(p.risk_notes)
# Flag openclaw @ claude_cli for manual review: succeeds frequently but poor change audit trail.
# Poor change evidence may reflect a backend design limitation, not a signal of incorrectness.
```

---

## Example 4: Small sample — weak evidence, no recommendations

```python
# records: 3 runs only — brand new backend

report = service.analyze(records)

print(report.comparison_summaries[0].evidence_strength)  # EvidenceStrength.WEAK
print(report.recommendations)  # []

# Only finding is sparse_data
for f in report.findings:
    print(f.category, f.summary)
# sparse_data   kodo @ claude_cli has only 3 sample(s) — too few for confident routing strategy conclusions.

# Limitations surfaced
for lim in report.limitations:
    print(lim)
# Only 3 record(s) available; most findings will have weak evidence...
# No execution duration data found in record metadata...
```

---

## Example 5: Validation coverage gap

```python
# records: 20 runs with validation always skipped

report = service.analyze(records)

s = report.comparison_summaries[0]
print(s.validation_skip_rate)   # 1.0
print(s.validation_pass_rate)   # 0.0

for f in report.findings:
    if f.category == "validation":
        print(f.summary)
# kodo @ claude_cli skips validation in 100% of runs, limiting quality signal.

for p in report.recommendations:
    if p.affected_policy_area == "validation_requirements":
        print(p.proposed_change)
# For kodo @ claude_cli on risk=medium or risk=high: policy should require at least one validation_command.
```

---

## Example 6: Per-task-type comparison

```python
from operations_center.tuning import compare_by_task_type

# Group records by (lane, backend, task_type) using task_type from metadata
summaries = compare_by_task_type(records)

for s in summaries:
    print(f"{s.backend} @ {s.lane} [{s.task_type_scope}]: "
          f"success={s.success_rate:.0%} n={s.sample_size}")

# kodo @ aider_local ['bug_fix']:   success=92% n=25
# kodo @ aider_local ['feature']:   success=61% n=12
# archon @ claude_cli ['refactor']: success=88% n=8
```

---

## Example 7: Explicit limitations in every report

```python
report = service.analyze(records)

print("=== Limitations ===")
for lim in report.limitations:
    print(f"• {lim}")

# Example output:
# • No execution duration data found in record metadata.
#   Latency class is UNKNOWN for all comparisons.
# • All records have skipped validation.
#   Validation quality cannot be assessed.
# • No records carry task_type metadata.
#   Per-task-type comparison is unavailable.
```

---

## Example 8: Dependency injection for testing

```python
from operations_center.tuning import StrategyTuningService, BackendComparisonSummary
from operations_center.tuning.routing_models import EvidenceStrength, ReliabilityClass, ChangeEvidenceClass

stub_summary = BackendComparisonSummary(
    backend="stub",
    lane="stub_lane",
    sample_size=10,
    evidence_strength=EvidenceStrength.MODERATE,
    success_rate=0.5,
    failure_rate=0.5,
    partial_rate=0.0,
    reliability_class=ReliabilityClass.LOW,
    change_evidence_class=ChangeEvidenceClass.STRONG,
)

def stub_compare(records, **kw):
    return [stub_summary]

service = StrategyTuningService(compare_fn=stub_compare)
report = service.analyze(records)
# report.comparison_summaries[0].backend == "stub"
# Useful for isolating test cases from real comparison logic
```
