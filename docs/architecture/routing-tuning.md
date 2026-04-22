# Evidence-Driven Routing and Backend Strategy Tuning (Phase 13)

## Why this exists

Before Phase 13, the system's routing posture was entirely static: a handcrafted policy model in SwitchBoard that did not change based on observed execution outcomes.

That means the system may be wrong about:
- when `aider_local` is good enough vs. when premium backends win
- when backends are unreliable for certain task types
- when OpenClaw's weaker changed-file evidence matters for a use case
- where validation coverage is a gap

Phase 13 adds a bounded, inspectable analysis layer that reads retained execution evidence and produces reviewable strategy inputs without automating any routing policy change.

---

## Architecture position

```
ExecutionRecords (retained by observability layer)
    ↓
StrategyTuningService.analyze(records)
    ↓
┌──────────────────────────────────────────┐
│  BackendComparisonSummary (per lane+backend) │
│  StrategyFinding (bounded observations)     │
│  RoutingTuningProposal (candidate changes)  │
│  StrategyAnalysisReport (full output)       │
└──────────────────────────────────────────┘
    ↓
Human reviewer
    ↓ (if accepted)
SwitchBoard routing policy update (future phase)
```

**The tuning layer is read-only with respect to active policy.** It never modifies `PolicyConfig`, `LaneRoutingPolicy`, or any active routing rule. All output is inspectable and subject to human review before any config change.

---

## Separation of concerns

| Layer | Owns |
|-------|------|
| Observability | Retained ExecutionRecords and ExecutionTraces |
| Strategy tuning | Analysis, comparison, findings, proposals |
| SwitchBoard | Active route selection and current policy |
| Policy/guardrails | Hard enforcement boundaries |

The three things that must remain separate:

1. **Current active routing policy** — what SwitchBoard applies today
2. **Observed historical evidence** — what ExecutionRecords show happened
3. **Proposed strategy changes** — candidate tuning from evidence

A developer should always be able to tell which of these three a given object belongs to.

---

## Input: what the tuning layer reads

The tuning layer operates on `ExecutionRecord` objects (from the observability layer). It reads:

| Field | Used for |
|-------|----------|
| `result.success` | Success rate |
| `result.status` | Failure/timeout/cancel classification |
| `result.failure_category` | NO_CHANGES, TIMEOUT, POLICY_BLOCKED |
| `validation_evidence.status` | Validation coverage |
| `changed_files_evidence.status` | Change evidence quality |
| `backend`, `lane` | Grouping key |
| `metadata["duration_ms"]` | Latency class (if available) |
| `metadata["task_type"]` | Per-task-type analysis |
| `metadata["risk_level"]` | Per-risk-level analysis |

**Known limitations:**
- Execution duration is not in `ExecutionResult` or `ExecutionRecord` by default — it must be in `metadata["duration_ms"]` to enable latency analysis.
- Validation quality is 0 when all runs skip validation.
- Task-type and risk-level breakdowns require metadata populated by callers.

---

## Comparison dimensions

Each `BackendComparisonSummary` covers one (lane, backend) combination:

| Dimension | Derived from |
|-----------|-------------|
| `success_rate` | `result.success` |
| `failure_rate` | status FAILED/CANCELLED/TIMEOUT |
| `partial_rate` | failure_category NO_CHANGES |
| `timeout_rate` | failure_category TIMEOUT |
| `validation_pass_rate` | validation_evidence PASSED |
| `validation_skip_rate` | validation_evidence SKIPPED |
| `change_evidence_class` | changed_files_evidence status distribution |
| `latency_class` | metadata["duration_ms"] median |
| `reliability_class` | success_rate thresholds |
| `evidence_strength` | sample_size |

---

## Classification enums

### EvidenceStrength
| Value | Condition |
|-------|-----------|
| `WEAK` | < 8 samples |
| `MODERATE` | 8–19 samples |
| `STRONG` | ≥ 20 samples |

### ReliabilityClass
| Value | Condition |
|-------|-----------|
| `HIGH` | success_rate ≥ 0.85 |
| `MEDIUM` | 0.60 ≤ success_rate < 0.85 |
| `LOW` | success_rate < 0.60 |

### ChangeEvidenceClass
| Value | Condition |
|-------|-----------|
| `STRONG` | ≥ 80% of runs have KNOWN or NONE changed-file status |
| `PARTIAL` | 40–79% have KNOWN or NONE |
| `POOR` | < 40% have KNOWN or NONE |
| `UNKNOWN` | All runs are NOT_APPLICABLE or no applicable runs |

### LatencyClass
| Value | Condition |
|-------|-----------|
| `FAST` | median < 30 s |
| `MEDIUM` | 30–120 s |
| `SLOW` | > 120 s |
| `UNKNOWN` | No duration_ms in metadata |

---

## Evidence flow

```
analyze(records)
  ↓
compare_backends(records)   → list[BackendComparisonSummary]
  ↓
derive_findings(summaries)  → list[StrategyFinding]
  ↓
generate_recommendations(findings) → list[RoutingTuningProposal]
  ↓
StrategyAnalysisReport (frozen, human-reviewable)
```

### Finding categories
- `sparse_data` — too few samples; no other findings generated
- `reliability` — success/failure rate patterns
- `change_evidence` — changed-file evidence quality
- `validation` — validation coverage gap
- `latency` — slow execution class
- `contradictory` — conflicting signals (e.g. high success, poor change evidence)

### Recommendation policy
- Recommendations are only generated from `MODERATE` or `STRONG` evidence.
- `WEAK` evidence findings produce no recommendations.
- All recommendations have `requires_review=True` — Phase 13 does not auto-apply anything.
- Each proposal carries `source_finding_ids` for traceability.

---

## Recommendation posture

Phase 13 recommendations are conservative and reviewable:

| Category | Proposal policy area |
|----------|---------------------|
| Low reliability | `backend_preference` — consider demoting |
| High reliability | `backend_preference` — consider increasing |
| High timeout rate | `escalation_threshold` — consider adjusting timeout |
| Poor change evidence | `backend_preference` — restrict to non-audit workflows |
| High validation skip rate | `validation_requirements` — consider requiring validation |
| Slow latency | `local_first_threshold` — consider faster lane |
| Contradictory | `backend_preference` — flag for manual review |

---

## Honest limitations

Every `StrategyAnalysisReport` carries a `limitations` list. These are not bugs — they are honest statements about what the analysis cannot determine.

Common limitations surfaced:
- Latency data unavailable (no `duration_ms` in metadata)
- All validation skipped (cannot assess validation quality)
- Missing lane/backend metadata (groups appear under "unknown")
- No task_type metadata (per-task-type comparison unavailable)
- Small sample size (findings are WEAK; no recommendations generated)

---

## File map

```
src/control_plane/tuning/
  routing_models.py     — BackendComparisonSummary, StrategyFinding,
                          RoutingTuningProposal, StrategyAnalysisReport,
                          EvidenceStrength, ReliabilityClass, ChangeEvidenceClass, LatencyClass
  compare.py            — compare_backends(), compare_by_task_type()
  routing_recommend.py  — derive_findings(), generate_recommendations()
  analyze.py            — StrategyTuningService (primary entry point)
  __init__.py           — public API exports

  [existing, unchanged]
  models.py             — FamilyMetrics, TuningRecommendation, TuningChange (proposal-creation tuning)
  metrics.py            — aggregate_family_metrics
  recommendations.py    — RecommendationEngine (proposal-creation tuning)
  service.py            — TuningRegulatorService (proposal-creation tuning)
  guardrails.py         — TuningGuardrails
  applier.py, loader.py, artifact_writer.py, calibration.py

tests/unit/tuning/
  conftest.py           — make_record(), make_success(), make_failure(), etc.
  test_routing_models.py
  test_compare.py
  test_routing_recommend.py
  test_analyze.py
  test_fixture_scenarios.py

tests/fixtures/tuning/
  local_success_dominant.json
  premium_backend_wins.json
  weak_change_evidence.json
  small_sample_weak_evidence.json
```
