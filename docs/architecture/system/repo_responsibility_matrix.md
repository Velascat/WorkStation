# Repository Responsibility Matrix

Authoritative record of what each system component owns, what it explicitly does not
own, what it consumes, and what it produces.

Cross-reference with [`system_overview.md`](system_overview.md) for the call-flow
context and [`ownership.md`](ownership.md) for the file-level ownership model within
this repo.

---

## PlatformDeployment

**Primary responsibility:** Local infrastructure platform. Everything required to make
services run on a developer machine.

**Secondary responsibility:** Tiny local model deployment for the `aider_local` lane.

| Field | Detail |
|-------|--------|
| **Inputs** | Operator config files, `.env` overrides, source repos for built services |
| **Outputs** | Running containers (SwitchBoard, Plane), deployed tiny models, health status |
| **Dependencies** | Docker, docker-compose, Plane setup script (makeplane releases) |
| **Invokes** | Nothing at runtime. Lifecycle scripts manage containers. |
| **Invoked by** | Operator via scripts or OperatorConsole. OperationsCenter's `manage.sh` delegates plane lifecycle here. |

**In scope:**
- Dockerfiles for every service in the shared stack
- Docker Compose manifests and profile variants
- Stack lifecycle commands (`up`, `down`, `restart`, `health`, `status`, `logs`)
- Port assignments and network topology
- Volume definitions and data persistence configuration
- Environment variable injection and secrets mounting
- Startup ordering and health-gate logic
- Plane infrastructure (separate script-managed stack)
- Deployment and serving of tiny local models for `aider_local` lane

**Out of scope — PlatformDeployment does not own:**
- What SwitchBoard's policy rules do or how lanes are scored
- What OperationsCenter decides to work on next
- What DAGExecutor's workflow steps are
- TeamExecutor's execution logic or agent orchestration
- Service-internal config schemas (those live in their own repos)
- Task prioritization logic of any kind
- The coding execution that happens inside a lane

---

## SwitchBoard

**Primary responsibility:** Execution-lane selector. Evaluates declarative policy to
choose which execution lane handles a given task.

**Secondary responsibility:** Request classification (inferring task complexity, cost
sensitivity, urgency) to feed lane scoring.

| Field | Detail |
|-------|--------|
| **Inputs** | Task request with metadata (complexity hints, cost flags, capability requirements) |
| **Outputs** | Selected lane name + downstream routing info; decision log entry |
| **Dependencies** | Policy YAML, profiles YAML, capability registry |
| **Invokes** | Nothing at runtime; SwitchBoard emits routing metadata only |
| **Invoked by** | OperationsCenter, or any system component that needs a lane assigned |

**Lanes SwitchBoard selects between:**
- `claude_cli` — Claude Code CLI, premium, OAuth/subscription
- `codex_cli` — Codex CLI, premium, OpenAI subscription
- `aider_local` — Aider with PlatformDeployment tiny models, local, free

**In scope:**
- Request classification (task type, complexity, estimated cost, urgency)
- Policy evaluation (ordered rules → lane selection)
- Multi-factor lane scoring (quality, cost, latency)
- Adaptive lane health monitoring (demote unhealthy lanes)
- A/B experiment routing
- Full audit trail of every lane selection decision
- Profile/capability registry (which lanes support which requirements)
- Service-local `.env.example` and documented env contract

**Out of scope — SwitchBoard does not own:**
- Provider credential management (lanes handle their own auth)
- Forwarding or proxying API calls to external LLM providers
- The execution that happens inside the selected lane
- Task prioritization or strategic decisions about what to work on
- Workflow structure or multi-step execution discipline
- Deployment of models or infrastructure
- OperationsCenter's autonomy logic

> **SwitchBoard is a selector, not a proxy.** It chooses the lane; it does not
> impersonate a provider or sit in the request path between a client and an LLM API.

---

## OperationsCenter

**Primary responsibility:** Decision and execution engine. Observes repo state,
derives insights, decides what work matters next, and drives the autonomous task loop.

**Secondary responsibility:** Platform integration layer (Plane board client, team_executor
invocation wrapper, execution artifact analysis).

| Field | Detail |
|-------|--------|
| **Inputs** | Repo state (git history, lint/test signals, architecture metrics), Plane task board, retained execution artifacts |
| **Outputs** | Proposal candidates, Plane tasks, execution requests, outcome artifacts, autonomy cycle reports |
| **Dependencies** | Plane (task board), team_executor (execution backend), git |
| **Invokes** | backend adapters through its execution boundary, SwitchBoard, Plane API |
| **Invoked by** | Operator via CLI, OperatorConsole, or OpenClaw |

**In scope:**
- Repo observation (git signals, lint, test, architecture, benchmark, security)
- Insight derivation and signal normalization
- Proposal candidate generation with confidence scoring
- Bounded autonomy loop with suppression guardrails and budgets
- Plane board integration (task creation, state transitions, comments)
- policy-gated execution coordination and backend dispatch
- backend adapter ownership and execution artifact analysis
- SwitchBoard client adapter and lane selection usage
- Execution outcome classification (failure modes, regression detection)
- Self-tuning regulation (threshold recommendations)

**Out of scope — OperationsCenter does not own:**
- Workflow structure and multi-step execution discipline (that is Archon's job)
- Lane selection policy (that is SwitchBoard's job)
- Model deployment or infrastructure (that is PlatformDeployment's job)
- The Plane stack itself (PlatformDeployment owns Plane infra; OperationsCenter owns the client)

---

## Archon

**Primary responsibility:** Workflow harness. Imposes structured, reproducible,
multi-step execution on a coding task via a YAML-defined DAG.

**Secondary responsibility:** Multi-platform delivery of task results (Slack, Telegram,
GitHub, web UI, CLI).

| Field | Detail |
|-------|--------|
| **Inputs** | YAML workflow definition, codebase path, task prompt, lane/model config |
| **Outputs** | Executed workflow run with per-node artifacts, PR (if configured), structured outcome |
| **Dependencies** | Claude Agent SDK or Codex SDK (via AI clients), SQLite/PostgreSQL (run tracking), git |
| **Invokes** | Claude CLI lane or Codex CLI lane (via SDK clients) |
| **Invoked by** | OperationsCenter execution boundary, operator CLI, platform adapters |

**In scope:**
- YAML workflow loading, validation, and DAG execution
- Node types: prompt, bash, loop, approval, script
- Git worktree isolation per workflow run
- Multi-platform adapters (Slack, Telegram, GitHub, Discord, Web, CLI)
- Session management and resume support
- Workflow run tracking (SQLite/PostgreSQL)
- Bundled default workflows (fix-issue, smart-pr-review, idea-to-pr, etc.)

**Out of scope — DAGExecutor does not own:**
- Strategic decisions about what work to do (that is OperationsCenter's job)
- Lane selection policy (that is SwitchBoard's job)
- Infrastructure deployment (that is PlatformDeployment's job)
- TeamExecutor's agent orchestration logic

---

## TeamExecutor

**Primary responsibility:** Coding execution backend. Orchestrates a multi-agent
coding session within a single task run.

**Secondary responsibility:** Multi-backend support (Claude Agent SDK, Codex SDK);
structured artifact output.

| Field | Detail |
|-------|--------|
| **Inputs** | Task description, repo path, execution parameters (lane, model, budget) |
| **Outputs** | Code changes (committed to branch), validation results, diff artifacts, outcome JSON |
| **Dependencies** | Claude Agent SDK or Codex SDK; git |
| **Invokes** | Claude CLI (via SDK), Codex CLI (via subprocess + JSONL), aider (via subprocess) |
| **Invoked by** | OperationsCenter, DAGExecutor (within workflow nodes) |

**In scope:**
- Multi-agent coding session orchestration
- Claude Agent SDK integration (subscription billing; strips API key before connect)
- Codex CLI subprocess integration (`codex exec`, JSONL output parsing)
- Aider subprocess integration
- Execution budget tracking and safety limits
- Validation command execution and failure classification
- Artifact writing (diff, stdout, stderr, outcome summary)

**Out of scope — TeamExecutor does not own:**
- System-wide policy or lane selection (that is SwitchBoard's job)
- Task proposal and prioritization (that is OperationsCenter's job)
- Workflow structure and multi-step DAG (that is DAGExecutor's job)
- Infrastructure deployment (that is PlatformDeployment's job)
- Long-range strategy about what repos to improve

---

## OpenClaw

**Primary responsibility:** Optional outer operator shell. Human-facing runtime that
sits above OperationsCenter and provides a unified control surface.

**Secondary responsibility:** Session management, workspace ergonomics, operator UX.

| Field | Detail |
|-------|--------|
| **Inputs** | Operator commands, context files, platform events |
| **Outputs** | Directed work requests to OperationsCenter, workspace state |
| **Dependencies** | OperationsCenter, PlatformDeployment lifecycle scripts |
| **Invokes** | OperationsCenter (directs what to work on), PlatformDeployment scripts (stack lifecycle) |
| **Invoked by** | Human operator |

**In scope:**
- Operator-facing entrypoints and command surface
- Session and workspace management
- Context file management
- Human-in-the-loop control over the autonomy loop

**Out of scope — OpenClaw does not own:**
- OperationsCenter's autonomy logic
- SwitchBoard's lane selection
- Any core execution or infrastructure

> **OpenClaw is optional.** The system (OperationsCenter through TeamExecutor) functions without
> it. OpenClaw adds operator ergonomics on top of an already-functioning autonomous
> system.

---

## Lane Responsibility Summaries

### Claude CLI Lane

| Field | Detail |
|-------|--------|
| **Invoked by** | TeamExecutor (via Claude Agent SDK `client.connect()`) |
| **Auth** | OAuth / Claude.ai subscription — no API key |
| **Strengths** | Highest capability, complex reasoning and refactors |
| **Cost profile** | Premium (subscription) |
| **PlatformDeployment role** | Runs on host machine; no PlatformDeployment deployment needed |

### Codex CLI Lane

| Field | Detail |
|-------|--------|
| **Invoked by** | TeamExecutor (via `codex exec` subprocess + JSONL) |
| **Auth** | OpenAI subscription — no API key |
| **Strengths** | Strong code generation, OpenAI subscription billing |
| **Cost profile** | Premium (subscription) |
| **PlatformDeployment role** | Runs on host machine; no PlatformDeployment deployment needed |

### aider local Lane

| Field | Detail |
|-------|--------|
| **Invoked by** | TeamExecutor via subprocess or OperationsCenter execution boundary; SwitchBoard selects this lane but does not dispatch execution |
| **Auth** | None — hits locally deployed models only |
| **Strengths** | Zero external API cost, always available, fast for simple edits |
| **Cost profile** | Free / local compute only |
| **PlatformDeployment role** | PlatformDeployment deploys and serves the tiny models consumed by this lane |

---

## Dependency Summary

```
OpenClaw (optional)
  └─invokes─► OperationsCenter
                └─invokes─► SwitchBoard (lane selection)
                └─consumes─► CxRP (orchestration contracts)
                └─consumes─► SourceRegistry (fork tracking, library)
                └─dispatches via─► CoreRunner
                                     ├─consumes─► RxP (runtime contracts)
                                     └─runs adapters─► team_executor / dag_executor / openclaw / direct_local / aider_local
                                                         └─each─► claude_cli / codex_cli / aider_local lane
                                                                    └─uses─► tiny models (PlatformDeployment)

PlatformDeployment
  └─deploys─► SwitchBoard
  └─deploys─► tiny local models
  └─manages─► Plane infra

Custodian
  └─audited by─► every consumer repo via .custodian/config.yaml + optional _custodian/ overlay
```

## New repos (extracted 2026-04..05)

| Repo | Role | Consumed by |
|------|------|-------------|
| **CxRP** | Orchestration contracts | OperationsCenter, SwitchBoard, OperatorConsole |
| **RxP** | Runtime contracts | OperationsCenter, CoreRunner |
| **CoreRunner** | Generic runtime mechanics; dispatch-by-runtime_kind | OperationsCenter (every backend adapter) |
| **SourceRegistry** | Source/fork tracking | OperationsCenter (library) |
| **Custodian** | Audit framework | Every repo (via `.custodian/config.yaml`) |
