# Startup Flow

This document describes the numbered steps to go from a clean checkout to a fully running, healthy WorkStation stack.

---

## Steps

### 1. Bootstrap (first time only)

Copy all example configuration files to their live locations and pull Docker images.

**Linux / macOS:**
```bash
cp .env.example .env
cp config/switchboard/policy.example.yaml   config/switchboard/policy.yaml
cp config/workstation/endpoints.example.yaml config/workstation/endpoints.yaml
```

**Windows (PowerShell):**
```powershell
.\scripts\bootstrap.ps1
```

Review `.env` and the config files. No extra provider-control service is required in the default architecture.

---

### 2. Pull images

Ensure Docker has the latest images for both services.

**Linux / macOS:**
```bash
docker compose -f compose/docker-compose.yml pull
```

**Windows:**
```powershell
.\scripts\bootstrap.ps1 -Pull
```

---

### 3. Start the stack

```bash
./scripts/up.sh
```

`up.sh` starts required services, waits for each to become healthy, and prints a per-component status. It exits non-zero if SwitchBoard does not start — the platform is not usable without it.

Expected output:
```
=== WorkStation: starting platform ===

[WorkStation] Validating environment...            [OK]

[WorkStation] Starting SwitchBoard...
  ...
[WorkStation] Waiting for SwitchBoard on :20401 (up to 60s)...
[WorkStation] SwitchBoard (http://localhost:20401) [OK]

[WorkStation] Checking Plane...
[WorkStation] Plane                                [SKIP] set PLANE_ENABLED=true in .env to enable

[WorkStation] Checking local lane (aider_local)...
[WorkStation] aider                                [WARN] binary not found — aider_local lane unavailable

=== WorkStation ready ===

  SwitchBoard      http://localhost:20401

  health  →  bash scripts/health.sh
  status  →  bash scripts/status.sh
  logs    →  bash scripts/logs.sh
  stop    →  bash scripts/down.sh
```

Running `up.sh` a second time is safe — `docker compose up --detach` reuses running containers and the health check returns immediately.

**Optional: start Plane**

Set `PLANE_ENABLED=true` in `.env` to have `up.sh` start Plane automatically. Plane failure is non-blocking — the script warns and continues.

---

### 4. Ready

The stack is ready to accept routing requests. Send a canonical proposal to SwitchBoard:

```bash
curl -s \
  -H "Content-Type: application/json" \
  -d '{"task_id":"demo-1","project_id":"workstation-demo","task_type":"documentation","execution_mode":"goal","goal_text":"Refresh README wording","target":{"repo_key":"docs","clone_url":"https://example.invalid/docs.git","base_branch":"main","allowed_paths":[]},"priority":"normal","risk_level":"low","constraints":{"allowed_paths":[],"require_clean_validation":true},"validation_profile":{"profile_name":"default","commands":[]},"branch_policy":{"push_on_success":true,"open_pr":false},"labels":[]}' \
  http://localhost:20401/route
```

---

## Stopping the Stack

**Linux / macOS:**
```bash
./scripts/down.sh
```

**Windows:**
```powershell
.\scripts\down.ps1
```

---

## Restart

**Windows:**
```powershell
.\scripts\restart.ps1
# or with image pull:
.\scripts\restart.ps1 -Pull
```

**Linux / macOS:**
```bash
./scripts/down.sh && ./scripts/up.sh
```

---

## Troubleshooting

| Symptom | Likely cause | Action |
|---------|-------------|--------|
| `up.sh` exits with `[FAIL] SwitchBoard` | Container failed to become healthy in 60 s | Run `bash scripts/logs.sh switchboard` to inspect |
| SwitchBoard fails health check after up | Config error in `config/switchboard/policy.yaml` | Fix config, then `bash scripts/restart.sh` |
| `docker compose` not found | Docker not installed or PATH issue | Install Docker Desktop / Docker Engine |
| Port conflict on :20401 | Another process using the port | Update `PORT_SWITCHBOARD` in `.env` and restart |
| Plane `[WARN]` in output | `PLANE_ENABLED=true` but Plane failed | Run `bash scripts/plane.sh status` to diagnose |
| `aider [WARN]` in output | `aider` not on PATH | Install aider or set up local model path |
