# Architecture

WorkStation is the local platform host for the current stack.

```text
ControlPlane -> SwitchBoard -> execution lane
                    ^
                    |
              WorkStation deploys and checks it
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
- [`docs/architecture/adr/0001-remove-9router.md`](architecture/adr/0001-remove-9router.md)
