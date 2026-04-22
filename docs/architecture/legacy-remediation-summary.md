# Legacy Remediation Summary

This remediation pass aligned the running system with the Phase 1–14 architecture.

## Removed from default runtime

- SwitchBoard provider-proxy wiring and `/v1/chat/completions` forwarding
- 9router-dependent health semantics
- WorkStation base compose dependency on 9router
- FOB provider-dashboard and provider-polling flows
- ControlPlane default worker/reviewer execution entrypoints

## Kept, but no longer mainline runtime

- Legacy execution modules quarantined in ControlPlane for temporary compatibility analysis
- Historical 9router ADR material
- Backend adapter modules that still implement canonical `ExecutionRequest -> ExecutionResult`

## Current runtime truth

```text
ControlPlane proposes work -> SwitchBoard selects how -> Adapters execute -> Observability records -> Policy constrains -> Tuning improves.
```

## Temporary shims

- ControlPlane's old execution service remains as legacy code only; default worker/reviewer entrypoints no longer invoke it.
