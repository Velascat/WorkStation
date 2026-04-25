# Local Lane Architecture: aider_local

This document describes the `aider_local` execution lane — what it is, why it lives
in WorkStation, and what WorkStation's responsibilities are and are not.

---

## What this lane is for

The `aider_local` lane exists to provide a cheap, locally-executable alternative to
premium execution lanes. Its intended uses are:

- **Cheap local assistance** — lint fixes, simple edits, and documentation tasks
  where tiny model quality is acceptable and API cost is not warranted.
- **Local-first execution experiments** — testing task flows without spending
  subscription credits on every run.
- **Reduced dependence on remote providers** — lower-tier tasks can run indefinitely
  on local hardware at zero marginal cost.
- **Bounded coding tasks where tiny models are acceptable** — straightforward,
  well-specified tasks with limited reasoning requirements.

This lane is not a replacement for premium reasoning. It is an always-available
complement.

---

## What this lane is not for

- **Premium reasoning replacement.** Complex refactors, architecture decisions, and
  multi-file transformations require a capable model. Use `claude_cli` or `codex_cli`
  for those.
- **Universal backend execution.** The lane does not replace other execution lanes.
  SwitchBoard selects between lanes; WorkStation just makes this one available.
- **Orchestration ownership.** WorkStation manages the lifecycle of the local model
  services. It does not decide when to use the lane, which tasks to assign, or what
  the routing policy is. That is SwitchBoard's job.
- **Repo-global decision policy.** Task proposal, confidence scoring, and strategic
  decision-making live in OperationsCenter. WorkStation reports availability; it does not
  shape the task queue.

---

## Why this lane lives in WorkStation

WorkStation owns local infrastructure and local capability lifecycle. The rule is:

> If it makes a service run, WorkStation owns it.

The `aider_local` lane requires locally deployed tiny model services. Those services
must be started, stopped, health-checked, and reported on. All of that is
infrastructure operation — WorkStation's domain.

The lane is definitively **not** a SwitchBoard concern (policy selection), a
OperationsCenter concern (task proposal), or a kodo concern (execution orchestration).
The line is clean:

| Concern | Owner |
|---------|-------|
| Deploying/starting the local model server | WorkStation |
| Checking if the lane is available | WorkStation |
| Deciding which lane to use for a task | SwitchBoard |
| Running Aider against the local models | kodo (`aider_local` backend process) |
| Deciding what task to run | OperationsCenter |

---

## Architecture position

```
OperationsCenter → SwitchBoard → [lane decision: aider_local]
                                       │
                                       ▼
                             kodo (aider_local runner)
                                       │
                                       ▼
                          Aider process (local subprocess)
                                       │
                                       ▼
                          Tiny model service (WorkStation-deployed)
                          e.g. Ollama serving qwen2.5-coder:1.5b
```

WorkStation sits outside this invocation chain. It deploys and runs the tiny model
service that OperationsCenter's execution boundary eventually calls. It also provides lifecycle management
and availability reporting that SwitchBoard can consult before assigning work.

---

## Lane hosting vs. lane selection

**Lane hosting** (WorkStation's job):
- Deploy and serve the local model
- Start, stop, and restart the model service
- Check whether the service is reachable
- Report lane state: `disabled`, `configured`, `starting`, `ready`, `unhealthy`, `stopped`, `failed`
- Report capability: what task classes the lane supports

**Lane selection** (SwitchBoard's job):
- Receive a task request with metadata
- Evaluate policy rules against the request
- Choose `aider_local`, `claude_cli`, or `codex_cli`
- Return the lane decision

WorkStation does not make routing decisions. SwitchBoard does not manage local
model processes. The boundary is explicit.

---

## Operational lifecycle

A clean lifecycle for the local lane looks like this:

1. **Configure** — copy `config/workstation/local_lane.example.yaml` to
   `local_lane.yaml`, set `lane.enabled: true`, configure model endpoints.

2. **Start** — run `python -m workstation_cli lane start aider_local`.
   WorkStation checks or starts configured model services, polls for readiness,
   and reports the final state.

3. **Check** — run `python -m workstation_cli lane status aider_local` or
   `lane health aider_local` to see live state.

4. **Use** — SwitchBoard queries availability; kodo sends requests to the local
   model endpoint when the lane is selected.

5. **Stop** — run `python -m workstation_cli lane stop aider_local` to stop
   any WorkStation-managed model processes cleanly.

---

## Local model services

WorkStation supports two small models configured in `local_lane.yaml`:

| Role | Default model | VRAM | Purpose |
|------|--------------|------|---------|
| Primary | `qwen2.5-coder:1.5b` | ~1 GB | Fast code-oriented edits |
| Secondary | `deepseek-coder:1.3b` | ~0.8 GB | Lighter, faster inference |

These defaults are chosen for constrained hardware (8 GB RAM). Both models run
comfortably via Ollama alongside a running development environment.

### Managed vs. externally-managed services

If `start_command` is set in the model config, WorkStation manages the process
lifecycle. If it is absent, WorkStation assumes the service is externally managed
(e.g. Ollama running as a system service) and only checks reachability.

---

## Lane states

| State | Meaning |
|-------|---------|
| `disabled` | `lane.enabled = false` in config |
| `configured` | Config loaded, services not checked or not yet started |
| `starting` | `start()` called, waiting for readiness |
| `ready` | All configured model services are reachable |
| `unhealthy` | Services started but not all reachable |
| `stopped` | Cleanly stopped via `stop()` |
| `failed` | Unrecoverable error; operator action needed |

---

## What this phase intentionally leaves unimplemented

Phase 2 establishes the local capability. The following are out of scope:

- SwitchBoard integration (Phase 4) — SwitchBoard consulting WorkStation availability
- OperationsCenter-to-WorkStation availability API (future phase)
- Cross-repo orchestration
- Queue or scheduler integration
- Automatic model download or provisioning
- Distributed deployment
- Multiple concurrent lane instances

These will be addressed in later phases when contracts are finalised.
