# Lane Readiness

Operator setup focuses on the execution lanes that SwitchBoard may select.

## What to check

| Concern | Owner | How to verify |
|---------|-------|---------------|
| Selector availability | SwitchBoard | `curl http://localhost:20401/health` |
| Local execution lane | WorkStation | `python -m workstation_cli lane status aider_local` |
| Premium CLI lanes | User environment | Verify the relevant CLI (`claude`, `codex`) is installed and authenticated |

## OperatorConsole shortcut

```bash
console providers
```

The command reports selector and lane readiness for the current architecture.

## Notes

- `aider_local` depends on WorkStation-managed local model services.
- Premium lanes are selected by SwitchBoard policy but authenticated outside WorkStation.
- The default WorkStation stack runs without any provider dashboard.
