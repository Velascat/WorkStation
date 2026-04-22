# Upstream Patch Evaluation Examples

## Example 1: OpenClaw Changed-File Uncertainty

Observed evidence:

- recurring unknown changed-file evidence
- audit-sensitive tasks are materially degraded
- adapter workaround is brittle and high-complexity

Expected evaluation result:

- strong-evidence finding
- adapter workaround assessment that still records adapter-first as the baseline
- review-only proposal for a narrow upstream observability improvement

## Example 2: Archon Limitation With Weak Evidence

Observed evidence:

- isolated provider/workflow limitation
- only one or two retained incidents

Expected evaluation result:

- weak-evidence finding
- no patch proposal
- document the limitation and continue using the adapter layer

## Example 3: kodo Ergonomic Friction

Observed evidence:

- recurring wrapper inconvenience
- workaround remains stable
- impact is mostly ergonomic, not architectural

Expected evaluation result:

- issue can still be logged as recurring
- no upstream patch proposal is recommended
- adapter-first continues to be preferred

## Example 4: High-Value Proposal With High Divergence Risk

Observed evidence:

- recurring brittle parsing or missing structured output
- large value if solved upstream
- high fork or merge-maintenance risk

Expected evaluation result:

- proposal may still be generated
- divergence risk and maintenance burden must be explicit
- proposal remains review-only until accepted as normal roadmap work
