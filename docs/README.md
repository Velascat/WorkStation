# PlatformDeployment Documentation

Index for the `docs/` tree.

`PlatformDeployment` is the current repository identity for the
`PlatformDeployment` plane. It owns local deployment, hosting, and
machine-specific topography concerns.

Public-facing ecosystem doctrine and charter material now live in
`ProtocolWarden.github.io`. PlatformDeployment docs are operational and
deployment-oriented, not the canonical public architecture charter.

## Architecture (deployment-focused)

These documents describe deployment, hosting, and local stack behavior.
They may provide detailed implementation notes, but they are not the
canonical public source of truth for ecosystem-wide ownership doctrine.

### System

- [architecture/system/system_overview.md](architecture/system/system_overview.md) —
  Full platform design and component roles.
- [architecture/system/ownership.md](architecture/system/ownership.md) —
  Repo-level ownership model.
- [architecture/system/repo_responsibility_matrix.md](architecture/system/repo_responsibility_matrix.md) —
  Tabular ownership matrix.
- [architecture/system/glossary.md](architecture/system/glossary.md) —
  Cross-repo terminology.
- [architecture/adr/](architecture/adr/) — Architecture decision records.
  - [architecture/adr/0001-remove-9router.md](architecture/adr/0001-remove-9router.md) —
    Decision to retire the 9router prototype.

### Routing

- [architecture/routing/operations-center-routing.md](architecture/routing/operations-center-routing.md) ·
  [examples](architecture/routing/operations-center-routing-examples.md)
- [architecture/routing/routing-fallback-escalation.md](architecture/routing/routing-fallback-escalation.md) ·
  [examples](architecture/routing/routing-fallback-escalation-examples.md)
- [architecture/routing/routing-tuning.md](architecture/routing/routing-tuning.md) ·
  [examples](architecture/routing/routing-tuning-examples.md)

### Adapters

- [architecture/adapters/openclaw-backend-adapter.md](architecture/adapters/openclaw-backend-adapter.md) ·
  [examples](architecture/adapters/openclaw-backend-adapter-examples.md)
- [architecture/adapters/openclaw-outer-shell.md](architecture/adapters/openclaw-outer-shell.md) ·
  [examples](architecture/adapters/openclaw-outer-shell-examples.md)
- [architecture/adapters/local-lane.md](architecture/adapters/local-lane.md)

### Contracts

- [architecture/contracts/contracts.md](architecture/contracts/contracts.md) ·
  [examples](architecture/contracts/contracts-examples.md)
- [architecture/contracts/upstream-patch-evaluation.md](architecture/contracts/upstream-patch-evaluation.md) ·
  [examples](architecture/contracts/upstream-patch-evaluation-examples.md)

### Execution

- [architecture/execution/execution-observability.md](architecture/execution/execution-observability.md) ·
  [examples](architecture/execution/execution-observability-examples.md)

### Policy

- [architecture/policy/policy-guardrails.md](architecture/policy/policy-guardrails.md) ·
  [examples](architecture/policy/policy-guardrails-examples.md)

### High-level overview

- [architecture.md](architecture.md) — Top-level architecture entry-point doc
  (kept at the root for inbound links; new material goes under
  `architecture/<subdir>/`).

## Operations

Day-to-day runbook material for operating the local stack.

- [operations/runbook.md](operations/runbook.md) — Day-to-day operational runbook
  (start/stop/health/troubleshoot, plus the Custodian boundary-artifact wrapper).
- [operations/local-lane-setup.md](operations/local-lane-setup.md) — Local lane
  (aider_local) tiny-model deployment.
- [operations/local_aider_lane.md](operations/local_aider_lane.md) — Operator
  notes for the `aider_local` lane.
- [operations/health-model.md](operations/health-model.md) — Health-check policy
  across services.
- [operations/environments.md](operations/environments.md) — Environment
  topology.
- [operations/port-map.md](operations/port-map.md) — Port assignments.
- [operations/service-map.md](operations/service-map.md) — Per-service map.
- [operations/startup-flow.md](operations/startup-flow.md) — Startup sequencing.

## Reference

- [reference/providers.md](reference/providers.md) — LLM provider surface
  reference.

## System

- [system/roadmap.md](system/roadmap.md) — Planned work, out-of-scope items.

## History

- [history/](history/) — Final-phase checklists, legacy remediation summaries,
  the historical 9router removal notes, and other one-shot historical material.
