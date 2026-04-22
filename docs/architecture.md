# Architecture

WorkStation is the local platform host for the current stack.

```text
ControlPlane proposes work -> SwitchBoard selects lane/backend -> adapters execute
                                       ^               ^
                                       |               |
                        WorkStation deploys services    local lane infra
```

WorkStation owns:

- SwitchBoard deployment and health checks
- local lane infrastructure for `aider_local`
- endpoint/status configuration
- compose scripts and operator utilities

Current reference docs:

- [`docs/architecture/system_overview.md`](architecture/system_overview.md)
- [`docs/architecture/repo_responsibility_matrix.md`](architecture/repo_responsibility_matrix.md)
- [`docs/architecture/ownership.md`](architecture/ownership.md)
