# Infrastructure Ownership

This document is the authoritative ownership model for the platform. When you
are deciding where a new file belongs, read this first.

---

## The rule

> If it makes a service **run**, `WorkStation` owns it.
> If it defines what a service **does**, the service repo owns it.

No exceptions without documentation (see [Exceptions](#exceptions)).

---

## Ownership matrix

| Artifact | Owner | Examples |
|----------|-------|---------|
| Dockerfiles (stack deployment) | `WorkStation` | `docker/Dockerfile.switchboard`, `docker/Dockerfile.9router` |
| Docker Compose manifests | `WorkStation` | `compose/docker-compose.yml` |
| Stack lifecycle scripts | `WorkStation` | `scripts/up.sh`, `scripts/down.sh`, `scripts/health.sh` |
| Service ports, networks, volumes | `WorkStation` | compose service definitions |
| Health checks (stack level) | `WorkStation` | compose `healthcheck:` blocks |
| Startup order, dependency wiring | `WorkStation` | compose `depends_on:` |
| Reverse-proxy / ingress config | `WorkStation` | (when added) |
| Stack environment injection | `WorkStation` | `config/9router/.env`, `config/switchboard/*.yaml` |
| Platform dependency infra (Plane, 9router) | `WorkStation` | Plane compose service, 9router Dockerfile |
| Operator entrypoints / demo commands | `FOB` | `fob demo`, `fob brief` |
| Routing policy and model-selection logic | `SwitchBoard` | `config/policy.yaml`, `PolicyEngine`, `Selector` |
| Aider/client integration semantics | `SwitchBoard` | `test_aider_compat.py`, `scripts/aider.sh` |
| Autonomy loop and Plane/SwitchBoard usage | `ControlPlane` | `loop.py`, `SwitchBoardClient`, `PlaneClient` |
| Config schema and `.env.example` (per service) | each service repo | `SwitchBoard/.env.example`, `ControlPlane/.env.example` |
| Test doubles and isolated dev helpers | each service repo | mock gateways, fake stores |
| Operator UX and workspace ergonomics | `FOB` | session management, layout, mission files |

---

## Per-repo boundaries

### WorkStation

WorkStation is the composition root for the shared local/dev/demo stack.

**Owns:**
- Dockerfiles for every service in the shared stack (SwitchBoard, 9router, Plane, and any future service)
- All compose manifests and profile variants (dev, demo, prod)
- Stack lifecycle commands (`up`, `down`, `restart`, `health`, `logs`, `status`)
- Port assignments and network topology
- Volume definitions and data persistence configuration
- Environment variable injection and secrets mounting approach
- Startup ordering and health-gate logic
- Demo and smoke orchestration scripts

**Does not own:**
- What SwitchBoard's policy rules do
- How ControlPlane reasons about tasks
- What FOB's workspace looks like
- Service-internal config schemas

### SwitchBoard

SwitchBoard owns everything about how routing decisions are made.

**Owns:**
- Request classification logic
- Policy evaluation engine
- Model-selection semantics
- Profile and capability registry schemas
- Aider/client compatibility layer and reference client scripts (`scripts/aider.sh`)
- Service-local `.env.example` and documented env contract
- Decision log format
- All test doubles for routing and selection behavior

**Does not own:**
- The Dockerfile used to run SwitchBoard in the shared stack (that is `WorkStation`'s)
- Compose service definitions or port assignments
- Health checks in the stack (though the service provides a `/health` endpoint)

### ControlPlane

ControlPlane owns how autonomous agents reason, act, and use platform services.

**Owns:**
- Autonomy loop behavior and proposal/decision logic
- SwitchBoard client adapter and usage semantics (`SwitchBoardClient`)
- Plane client adapter and API usage semantics (`PlaneClient`)
- Executor adapters (Aider, Kodo) and how tasks are dispatched
- Task parsing and workflow semantics
- ControlPlane-local `.env.example` and documented env contract
- Test doubles for Plane, SwitchBoard, and executor interactions

**Does not own:**
- The Plane stack required to run Plane (that is `WorkStation`'s)
- The SwitchBoard stack (that is `WorkStation`'s)
- How FOB launches the operator workspace

### FOB

FOB owns the operator experience — how humans interact with the platform.

**Owns:**
- Session and workspace management (Zellij, Claude resume)
- Operator command entrypoints: `fob brief`, `fob demo`, `fob status`, etc.
- Layout definitions and mission file templates
- Human-facing orchestration that calls into WorkStation or service CLIs
- Demo command that proves the platform is working (`fob demo`)

**Does not own:**
- Platform stack lifecycle internals (delegates to WorkStation)
- Service business logic
- Infrastructure configuration

### 9router

9router is a platform dependency — a provider-routing service.

**Ownership:** `WorkStation` owns the Dockerfile and compose service.
9router has its own repo (`decolua/9router`) with its own application code.
WorkStation builds it from source.

### Plane

Plane is a platform dependency — a task-tracking and project-management service.

**Ownership:** `WorkStation` owns the Plane compose service and infrastructure.
ControlPlane owns the Plane client adapter and all usage semantics.

---

## Concrete examples

### Example A — SwitchBoard Dockerfile

A Dockerfile that builds and runs SwitchBoard as a container.

**Belongs in:** `WorkStation/docker/Dockerfile.switchboard`

**Why:** Making a service run is infrastructure. WorkStation is the composition root.

---

### Example B — SwitchBoard routing policy

`config/policy.yaml` defining which profile handles coding requests.

**Belongs in:** `SwitchBoard/config/policy.yaml`

**Why:** This defines routing behavior, not how to run the service.

---

### Example C — Plane local stack

A compose service definition for Plane (required by ControlPlane).

**Belongs in:** `WorkStation/compose/docker-compose.yml`

**Why:** Plane is a platform dependency. That ControlPlane needs it does not change where
the runnable infra lives. The service repo describes what it needs; WorkStation provides it.

---

### Example D — Plane API client

`ControlPlane/src/control_plane/adapters/plane/client.py` — Python adapter for the Plane API.

**Belongs in:** `ControlPlane`

**Why:** This is application behavior — how ControlPlane uses Plane. The usage semantics
belong to the consumer, not to the infrastructure layer.

---

### Example E — `fob demo`

An operator command that proves the full platform is working.

**Belongs in:** `FOB`

**Why:** This is an operator-facing entrypoint. FOB owns the operator experience.
The demo delegates lifecycle actions to WorkStation and service calls to SwitchBoard/ControlPlane.

---

### Example F — SwitchBoard `.env.example`

Documents required environment variables for SwitchBoard.

**Belongs in:** `SwitchBoard/.env.example`

**Why:** The service defines its own contract. WorkStation reads this contract
and injects appropriate values at runtime, but does not own the schema.

---

### Example G — Aider reference client scripts

`scripts/aider.sh` and `scripts/bootstrap_aider.sh` in SwitchBoard.

**Belongs in:** `SwitchBoard/scripts/`

**Why:** These are reference client fixtures used to validate SwitchBoard's
OpenAI-compatible API. They belong with the service they test. They are not
infrastructure — Aider is optional, not a required dependency.

---

## Exceptions

An exception is any case where a service repo other than `WorkStation` owns a
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

- [x] `WorkStation/docker/Dockerfile.switchboard` — created
- [x] `WorkStation/docker/Dockerfile.9router` — created
- [x] `WorkStation/compose/docker-compose.yml` — updated to build from source
- [x] Plane infrastructure — `WorkStation/scripts/plane.sh` is canonical; `ControlPlane/deployment/plane/manage.sh` delegates to it
- [x] `fob demo` command — implemented in `FOB/src/fob/demo.py`
- [ ] WorkStation `workstation_cli` not yet wired to `fob demo`

---

## Questions this answers

| Question | Answer |
|----------|--------|
| Where does a new service Dockerfile go? | `WorkStation/docker/` |
| Where do compose service definitions go? | `WorkStation/compose/docker-compose.yml` |
| Where does a health check script go? | `WorkStation/scripts/health.sh` |
| Where does service-local config schema go? | the service repo (e.g. `SwitchBoard/config/`) |
| Where does a demo/orchestration command go? | `FOB` |
| Where does Plane startup logic go? | `WorkStation` |
| Where does ControlPlane's Plane client go? | `ControlPlane` |
| Where does SwitchBoard's routing policy go? | `SwitchBoard` |
