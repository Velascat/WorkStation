# Infrastructure Ownership

This document is the authoritative ownership model for the platform. When you
are deciding where a new file belongs, read this first.

---

## The rule

> If it makes a service **run**, `PlatformDeployment` owns it.
> If it defines what a service **does**, the service repo owns it.

No exceptions without documentation (see [Exceptions](#exceptions)).

Related rule:

> If a backend limitation suggests upstream modification, evaluation and proposal
> discipline still live with the platform architecture. The upstream repo does
> not become the new center of the design by default.

---

## Ownership matrix

| Artifact | Owner | Examples |
|----------|-------|---------|
| Dockerfiles (stack deployment) | `PlatformDeployment` | `docker/Dockerfile.switchboard` |
| Docker Compose manifests | `PlatformDeployment` | `compose/docker-compose.yml` |
| Stack lifecycle scripts | `PlatformDeployment` | `scripts/up.sh`, `scripts/down.sh`, `scripts/health.sh` |
| Service ports, networks, volumes | `PlatformDeployment` | compose service definitions |
| Health checks (stack level) | `PlatformDeployment` | compose `healthcheck:` blocks |
| Startup order, dependency wiring | `PlatformDeployment` | compose `depends_on:` |
| Reverse-proxy / ingress config | `PlatformDeployment` | (when added) |
| Stack environment injection | `PlatformDeployment` | `config/switchboard/*.yaml` |
| Platform dependency infra (Plane) | `PlatformDeployment` | Plane compose service |
| Tiny local model deployment | `PlatformDeployment` | model serving scripts for `aider_local` lane |
| Operator entrypoints / demo commands | `OperatorConsole` | `console demo`, `console open` |
| Lane-routing policy and selector logic | `SwitchBoard` | `config/policy.yaml`, `LaneSelector`, `DecisionPlanner` |
| Autonomy loop and Plane/SwitchBoard usage | `OperationsCenter` | `loop.py`, `SwitchBoardClient`, `PlaneClient` |
| Config schema and `.env.example` (per service) | each service repo | `SwitchBoard/.env.example`, `OperationsCenter/.env.example` |
| Test doubles and isolated dev helpers | each service repo | mock gateways, fake stores |
| Operator UX and workspace ergonomics | `OperatorConsole` | session management, layout, context files |

---

## Per-repo boundaries

### PlatformDeployment

PlatformDeployment is the composition root for the shared local/dev/demo stack.

**Owns:**
- Dockerfiles for every service in the shared stack (SwitchBoard, Plane, and any future service)
- All compose manifests and profile variants (dev, demo, prod)
- Stack lifecycle commands (`up`, `down`, `restart`, `health`, `logs`, `status`)
- Port assignments and network topology
- Volume definitions and data persistence configuration
- Environment variable injection and secrets mounting approach
- Startup ordering and health-gate logic
- Demo and smoke orchestration scripts

**Does not own:**
- What SwitchBoard's policy rules do
- How OperationsCenter reasons about tasks
- What OperatorConsole's workspace looks like
- Service-internal config schemas

### SwitchBoard

SwitchBoard owns everything about how routing decisions are made.

**Owns:**
- Canonical lane-routing policy
- Lane selection and planning semantics
- Service-local `.env.example` and documented env contract
- Decision log format
- All test doubles for canonical routing behavior

**Does not own:**
- The Dockerfile used to run SwitchBoard in the shared stack (that is `PlatformDeployment`'s)
- Compose service definitions or port assignments
- Health checks in the stack (though the service provides a `/health` endpoint)

### OperationsCenter

OperationsCenter owns how autonomous agents reason, act, and use platform services.

**Owns:**
- Autonomy loop behavior and proposal/decision logic
- SwitchBoard client adapter and usage semantics (`SwitchBoardClient`)
- Plane client adapter and API usage semantics (`PlaneClient`)
- Executor adapters (Aider, TeamExecutor) and how tasks are dispatched
- Task parsing and workflow semantics
- OperationsCenter-local `.env.example` and documented env contract
- Test doubles for Plane, SwitchBoard, and executor interactions

**Does not own:**
- The Plane stack required to run Plane (that is `PlatformDeployment`'s)
- The SwitchBoard stack (that is `PlatformDeployment`'s)
- How OperatorConsole launches the operator workspace

### OperatorConsole

OperatorConsole owns the operator experience — how humans interact with the platform.

**Owns:**
- Session and workspace management (Zellij, Claude resume)
- Operator command entrypoints: `console open`, `console demo`, `console status`, etc.
- Layout definitions and context file templates
- Human-facing orchestration that calls into PlatformDeployment or service CLIs
- Demo command that proves the platform is working (`console demo`)

**Does not own:**
- Platform stack lifecycle internals (delegates to PlatformDeployment)
- Service business logic
- Infrastructure configuration

### Plane

Plane is a platform dependency — a task-tracking and project-management service.

**Ownership:** `PlatformDeployment` owns the Plane compose service and infrastructure.
OperationsCenter owns the Plane client adapter and all usage semantics.

### CxRP and RxP

Contract-only repos. CxRP holds the canonical orchestration types
(`TaskProposal`, `LaneDecision`, `ExecutionRequest`, `ExecutionResult`); RxP
holds runtime types (`RuntimeInvocation`, `RuntimeResult`, `ArtifactDescriptor`).

**Owns:**
- Versioned schemas (JSON Schema), vocabulary enums, validation helpers, examples
- Contract evolution policy

**Does not own:**
- Implementation, transport, scheduling, adapters, model integration

Consumer repos (OperationsCenter, SwitchBoard, OperatorConsole, CoreRunner)
import these types directly; OC additionally maps them to internal Pydantic
models via `cxrp_mapper.py`.

### CoreRunner

Generic runtime mechanics — dispatches RxP `RuntimeInvocation` by
`runtime_kind` to a registered runner.

**Owns:**
- `SubprocessRunner` (process-group safe), `ManualRunner`, `HttpRunner`
- Dispatch-by-`runtime_kind` registry
- Environment overlay, working-directory control, timeout enforcement,
  stdout/stderr capture, exit-code normalization, ArtifactDescriptor collection

**Does not own:**
- Orchestration, planning, lane selection
- Backend semantics (team_executor, dag_executor, openclaw belong to OperationsCenter)
- Source/fork tracking (belongs to SourceRegistry)

OC backend adapters (team_executor, dag_executor, openclaw, direct_local, aider_local) all
delegate subprocess execution through CoreRunner.

### SourceRegistry

Source and fork tracking layer. Resolves named source dependencies, verifies
expected SHAs across install kinds, records local-fork patches and
upstream-sync intent.

**Owns:**
- Registry (`SourceEntry`), verification (`VerificationResult`), lifecycle
  state, patch records, poll/push intent, CLI

**Does not own:**
- Subprocess execution (CoreRunner), workflow harness (Archon),
  fork pushing — SR records intent; the operator pushes

OperationsCenter consumes SR as a library.

### Custodian

Cross-repo audit and maintenance toolkit.

**Owns:**
- Detector framework (C/D/F/U/K/S/A/H/T/G/N/P/R classes)
- Adapters that wrap external tools (ruff, vulture, ty, semgrep, coverage)
- Plugin loader so consumer repos can extend with their own `_custodian/` overlays
- CLI: `custodian-doctor`, `custodian-audit`, `custodian-triage`

**Does not own:**
- Linting / formatting / type-checking (delegates to wrapped tools)
- Test running
- CI integration (consumer repos call Custodian from their own CI)

---

## Concrete examples

### Example A — SwitchBoard Dockerfile

A Dockerfile that builds and runs SwitchBoard as a container.

**Belongs in:** `PlatformDeployment/docker/Dockerfile.switchboard`

**Why:** Making a service run is infrastructure. PlatformDeployment is the composition root.

---

### Example B — SwitchBoard routing policy

`config/policy.yaml` defining which lane/backend handles coding requests.

**Belongs in:** `SwitchBoard/config/policy.yaml`

**Why:** This defines routing behavior, not how to run the service.

---

### Example C — Plane local stack

A compose service definition for Plane (required by OperationsCenter).

**Belongs in:** `PlatformDeployment/compose/docker-compose.yml`

**Why:** Plane is a platform dependency. That OperationsCenter needs it does not change where
the runnable infra lives. The service repo describes what it needs; PlatformDeployment provides it.

---

### Example D — Plane API client

`OperationsCenter/src/operations_center/adapters/plane/client.py` — Python adapter for the Plane API.

**Belongs in:** `OperationsCenter`

**Why:** This is application behavior — how OperationsCenter uses Plane. The usage semantics
belong to the consumer, not to the infrastructure layer.

---

### Example E — `console demo`

An operator command that proves the full platform is working.

**Belongs in:** `OperatorConsole`

**Why:** This is an operator-facing entrypoint. OperatorConsole owns the operator experience.
The demo delegates lifecycle actions to PlatformDeployment and service calls to SwitchBoard/OperationsCenter.

---

### Example F — SwitchBoard `.env.example`

Documents required environment variables for SwitchBoard.

**Belongs in:** `SwitchBoard/.env.example`

**Why:** The service defines its own contract. PlatformDeployment reads this contract
and injects appropriate values at runtime, but does not own the schema.

---

## Exceptions

An exception is any case where a service repo other than `PlatformDeployment` owns a
runtime/deployment artifact.

**Current exceptions:** none.

**How to add an exception:**

1. Document it in this file under a new subsection below.
2. State the artifact, the owning repo, the rationale, and the intended scope.
3. Note whether the exception is permanent or temporary.

If you are considering a silent exception (i.e., not documenting it), treat that
as a signal that the decision has not been thought through.

---

## Cleanup checklist

Current state as of the time this document was written (2026-04-21):

- [x] `PlatformDeployment/docker/Dockerfile.switchboard` — created
- [x] Plane infrastructure — `PlatformDeployment/scripts/plane.sh` is canonical; `OperationsCenter/deployment/plane/manage.sh` delegates to it
- [x] `console demo` command — implemented in `OperatorConsole/src/operator_console/demo.py`
- [ ] PlatformDeployment `platform_deployment_cli` not yet wired to `console demo`

---

## Questions this answers

| Question | Answer |
|----------|--------|
| Where does a new service Dockerfile go? | `PlatformDeployment/docker/` |
| Where do compose service definitions go? | `PlatformDeployment/compose/docker-compose.yml` |
| Where does a health check script go? | `PlatformDeployment/scripts/health.sh` |
| Where does service-local config schema go? | the service repo (e.g. `SwitchBoard/config/`) |
| Where does a demo/orchestration command go? | `OperatorConsole` |
| Where does Plane startup logic go? | `PlatformDeployment` |
| Where does OperationsCenter's Plane client go? | `OperationsCenter` |
| Where does SwitchBoard's routing policy go? | `SwitchBoard` |
