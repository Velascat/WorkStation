# WorkStation

WorkStation is the local developer platform that deploys and operates the shared model stack. It owns the lifecycle of **SwitchBoard** and **9router**, providing a single compose-based entrypoint for spinning up, inspecting, and tearing down the full stack on any developer machine or CI host.

---

## Architecture Overview

```
Client Request
     │
     ▼
┌──────────────┐
│  SwitchBoard  │  :20401  — routing policy, auth, rate-limiting
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   9router    │  :20128  — provider selection, model dispatch
└──────┬───────┘
       │
       ▼
   Providers  (OpenAI, Anthropic, local models, …)
```

- **WorkStation** — this repo; orchestrates the stack via Docker Compose.
- **SwitchBoard** — the policy and routing gateway. All client traffic enters here.
- **9router** — the model dispatcher. Receives normalised requests from SwitchBoard and routes to the appropriate provider.

---

## Quick Start

```bash
# 1. Copy environment config
cp .env.example .env

# 2. Pull images and start the stack
./scripts/up.sh

# 3. Verify everything is healthy
./scripts/health.sh
```

On Windows (PowerShell):

```powershell
./scripts/bootstrap.ps1   # first time only
./scripts/up.ps1
./scripts/health.ps1
```

---

## Ports

| Service     | Port  | Purpose                    |
|-------------|-------|----------------------------|
| SwitchBoard | 20401 | API gateway / policy layer |
| 9router     | 20128 | Model dispatch             |
| Status API  | 20400 | Stack health & metadata    |

---

## Repository Layout

```
WorkStation/
├── compose/                  Docker Compose files and profiles
│   ├── docker-compose.yml
│   ├── docker-compose.override.example.yml
│   └── profiles/
│       ├── core.yml
│       ├── dev.yml
│       └── observability.yml
├── config/
│   ├── switchboard/          SwitchBoard policy & profile config
│   ├── 9router/              9router environment config
│   └── workstation/          Endpoint registry
├── scripts/                  Bash + PowerShell helper scripts
├── docs/                     Architecture and operations docs
├── tools/workstation_cli/    Python CLI (workstation up/down/health/status)
└── test/                     Smoke + unit tests
```

---

## Configuration

All environment variables are documented in `.env.example`. Copy it to `.env` and adjust as needed.

Service-specific config lives under `config/`. Copy the `.example.*` files to their live names before starting:

```bash
cp config/switchboard/policy.example.yaml   config/switchboard/policy.yaml
cp config/switchboard/profiles.example.yaml config/switchboard/profiles.yaml
cp config/9router/.env.example              config/9router/.env
cp config/workstation/endpoints.example.yaml config/workstation/endpoints.yaml
```

---

## Scripts

| Script           | What it does                              |
|------------------|-------------------------------------------|
| `up.sh / up.ps1` | Start the stack in detached mode          |
| `down.sh / down.ps1` | Stop and remove containers            |
| `health.sh / health.ps1` | Curl health endpoints             |
| `status.sh / status.ps1` | Health + service summary          |
| `logs.ps1`       | Stream compose logs                       |
| `restart.ps1`    | down + up                                 |
| `bootstrap.ps1`  | First-time setup (copy .env, pull images) |

---

## Contributing

1. Fork the repo and create a feature branch.
2. Follow the existing file conventions.
3. Add or update tests under `test/`.
4. Open a pull request against `main`.

---

## License

MIT — see [LICENSE](LICENSE).
