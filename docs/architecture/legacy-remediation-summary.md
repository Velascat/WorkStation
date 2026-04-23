# Legacy Remediation Summary

Historical remediation note. This file records what was removed or quarantined
during cleanup; current architecture guidance lives in `system_overview.md` and
related canonical docs.

This remediation pass aligned the running system with the Phase 1–14 architecture.

## Removed from default runtime

- SwitchBoard provider-proxy wiring and `/v1/chat/completions` forwarding
- provider-router-dependent health semantics
- WorkStation base compose dependency on the retired provider router
- FOB provider-dashboard and provider-polling flows
- ControlPlane legacy worker/reviewer execution entrypoints

## Kept, but no longer mainline runtime

- Historical provider-router ADR material
- Backend adapter modules that still implement canonical `ExecutionRequest -> ExecutionResult`

## Current runtime truth

```text
ControlPlane proposes work -> SwitchBoard selects lane/backend
-> ControlPlane enforces policy and dispatches adapters
-> Observability records -> Tuning recommends improvements.
```

## Temporary shims

- No legacy execution runtime remains on the default path; the planning worker and canonical execute entrypoint now describe separate supported ControlPlane boundaries.
