# Architecture

> **This document is outdated.** It describes the old SwitchBoard → 9router proxy
> architecture. `9router` has been removed from the platform.
>
> The canonical architecture documentation is now in:
> - [`docs/architecture/system_overview.md`](architecture/system_overview.md) — full system description
> - [`docs/architecture/repo_responsibility_matrix.md`](architecture/repo_responsibility_matrix.md) — per-component responsibilities
> - [`docs/architecture/adr/0001-remove-9router.md`](architecture/adr/0001-remove-9router.md) — why 9router was removed
>
> The content below is preserved for historical reference only.

---

## Overview (historical)

WorkStation was a local developer platform that orchestrated a shared model stack composed of two services: **SwitchBoard** and **9router**. Together they formed a proxy layer that sat between client applications and AI model providers.

```
┌─────────────────────────────────────────────────────────────┐
│                        Client Layer                         │
│          (applications, notebooks, CLI tools, tests)        │
└──────────────────────────────┬──────────────────────────────┘
                               │  HTTP  :20401
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                        SwitchBoard                          │
│                         :20401                              │
│                                                             │
│  • Receives all inbound client requests                     │
│  • Enforces authentication (API key / JWT)                  │
│  • Applies routing policy (rules, profile resolution)       │
│  • Rate-limits by key or profile tier                       │
│  • Forwards authorised, annotated requests to 9router       │
└──────────────────────────────┬──────────────────────────────┘
                               │  HTTP  :20128
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                          9router                            │
│                         :20128                              │
│                                                             │
│  • Receives normalised requests from SwitchBoard            │
│  • Selects the best provider based on routing_hint,         │
│    availability, latency, or cost strategy                  │
│  • Translates requests into provider-specific wire format   │
│  • Returns provider responses to SwitchBoard                │
│  • Handles retries and failover across providers            │
└──────────┬──────────────────┬───────────────────┬───────────┘
           │                  │                   │
           ▼                  ▼                   ▼
      OpenAI API         Anthropic API       Other Providers
                                             (Cohere, Mistral,
                                              local models…)
```

---

## Layer Responsibilities

### WorkStation (this repo)

- Owns the Docker Compose configuration for the entire stack.
- Provides helper scripts for start / stop / health / status operations.
- Holds example configuration files for both downstream services.
- Provides the `workstation_cli` Python tool for programmatic control.
- Houses smoke tests that validate the running stack.

WorkStation does **not** participate in the request path at runtime. It is a pure infrastructure and operational concern.

### SwitchBoard (:20401)

SwitchBoard is the single entry point for all model API traffic. Its responsibilities are:

| Concern            | Detail                                                                 |
|--------------------|------------------------------------------------------------------------|
| Authentication     | Validates API keys or JWT tokens before requests proceed               |
| Policy enforcement | Applies rules defined in `config/switchboard/policy.yaml`             |
| Profile resolution | Maps named capability profiles (fast / standard / power) to routing hints |
| Rate limiting      | Enforces per-key or per-profile request rate caps                     |
| Upstream routing   | Forwards requests to 9router with enriched headers/metadata           |
| Observability      | Emits request/response logs; exposes `/health` and metrics endpoints  |

### 9router (:20128)

9router is the model dispatcher. It abstracts away provider-specific details. Its responsibilities are:

| Concern             | Detail                                                                   |
|---------------------|--------------------------------------------------------------------------|
| Provider selection  | Chooses the provider based on `routing_hint`, strategy, and availability |
| Format translation  | Converts requests to provider wire format (OpenAI, Anthropic, etc.)     |
| Retry / failover    | Retries on transient errors; fails over to alternate providers           |
| Response normalisation | Returns a consistent response shape to SwitchBoard                 |
| Credential management | Holds provider API keys; never exposed to clients                    |

---

## Network Topology

All services communicate over the `workstation-platform` Docker bridge network. From host to container, only the declared ports are published:

```
Host :20401  →  workstation-switchboard  :20401
Host :20128  →  workstation-ninerouter   :20128
Host :20400  →  status API               :20400  (future)
```

Inter-service traffic (SwitchBoard → 9router) travels over the internal network using Docker service-name DNS resolution (`http://ninerouter:20128`), so it never leaves the bridge.

---

## Configuration Flow

```
WorkStation repo
└── config/
    ├── switchboard/policy.yaml       →  mounted into SwitchBoard container
    ├── switchboard/profiles.yaml     →  mounted into SwitchBoard container
    ├── 9router/.env                  →  env_file for 9router container
    └── workstation/endpoints.yaml    →  read by workstation_cli + tests
```

Live config files are excluded from version control (see `.gitignore`). Only `.example.*` variants are committed. Operators copy and customise them before starting the stack.
