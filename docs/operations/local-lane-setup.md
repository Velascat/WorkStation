# Local Lane Setup: aider_local

This guide covers how to configure, start, and operate the `aider_local` execution
lane on a single developer machine.

---

## Hardware expectations

The `aider_local` lane is designed for **constrained hardware**. Typical requirements:

- 8 GB RAM (16 GB recommended if running other services simultaneously)
- No dedicated GPU required — CPU inference is supported but slower
- Single machine — no distributed deployment assumed

If you have a GPU with 4+ GB VRAM, inference will be significantly faster.
The default model choices (`qwen2.5-coder:1.5b`, `deepseek-coder:1.3b`) are
selected to fit comfortably in CPU RAM.

---

## Local-first assumptions

This lane assumes:
- All model services run on the same machine as WorkStation
- No external API calls or provider credentials are needed
- The lane may not be available during machine sleep/hibernate
- Startup time depends on model load time (typically 5–20 seconds with CPU)

---

## Step 1 — Install a model server

WorkStation expects the model service to expose a health endpoint. The recommended
server is **Ollama** (https://ollama.ai).

```bash
# macOS / Linux
curl -fsSL https://ollama.ai/install.sh | sh

# Verify installation
ollama --version
```

On Linux, Ollama runs as a systemd service after installation. On macOS, run
`ollama serve` in a terminal or add it to your login items.

---

## Step 2 — Pull the models

```bash
# Primary model (~1 GB)
ollama pull qwen2.5-coder:1.5b

# Secondary model (~0.8 GB)
ollama pull deepseek-coder:1.3b

# Verify
ollama list
```

---

## Step 3 — Configure the lane

Copy the example config and enable the lane:

```bash
cp config/workstation/local_lane.example.yaml config/workstation/local_lane.yaml
```

Open `config/workstation/local_lane.yaml` and set:

```yaml
lane:
  enabled: true         # change from false to true
```

If your Ollama instance runs on a non-default port, update the endpoints:

```yaml
models:
  - name: primary
    endpoint: "http://localhost:11434"   # Ollama default
```

If you want WorkStation to start Ollama automatically, add:

```yaml
models:
  - name: primary
    start_command: "ollama serve"
```

If Ollama is managed by systemd (typical Linux install), leave `start_command` null
and let WorkStation check reachability only.

---

## Step 4 — Check status

```bash
python -m workstation_cli lane status aider_local
```

If Ollama is running and models are loaded, you should see:

```
=== WorkStation: lane status ===

  Lane:   aider_local
  State:  READY

    [OK]    primary       http://localhost:11434
    [OK]    secondary     http://localhost:11435
```

If a model service is not reachable:

```
  Lane:   aider_local
  State:  UNHEALTHY
  Issue:  Model services unreachable: secondary

    [OK]    primary       http://localhost:11434
    [FAIL]  secondary     http://localhost:11435
              Connection refused
```

---

## Step 5 — Start managed services (optional)

If `start_command` is set in the config, WorkStation can start the services:

```bash
python -m workstation_cli lane start aider_local
```

This polls until all services are reachable (up to `startup_timeout_seconds`) and
reports the final state. Use this when you want a single command to bring the lane up.

---

## Stopping the lane

```bash
python -m workstation_cli lane stop aider_local
```

This terminates any processes started by WorkStation. Externally-managed services
(e.g. Ollama as a system service) are not affected.

---

## Command reference

| Command | What it does |
|---------|--------------|
| `python -m workstation_cli lane status aider_local` | Show current state and model health |
| `python -m workstation_cli lane health aider_local` | Run a live health check |
| `python -m workstation_cli lane start aider_local` | Start managed services, wait for readiness |
| `python -m workstation_cli lane stop aider_local` | Stop managed services |
| `python -m workstation_cli lane status --json aider_local` | Machine-readable status |
| `python -m workstation_cli lane health --json aider_local` | Machine-readable health check |

---

## What "ready" means

The lane is `READY` when **all configured model services** respond to a GET request
on their health path. For Ollama, this is `GET /api/tags` returning HTTP 200.

A partially-reachable lane (some models up, some down) reports `UNHEALTHY`, not
`READY`. Routing layers should treat any non-`READY` state as unavailable.

---

## Common failure cases

### "No model services configured"

`config/workstation/local_lane.yaml` has no entries under `models:`. Add at least
one model entry with `name`, `model_id`, and `endpoint`.

### "Model services unreachable: primary"

The model server is not running or not yet loaded. Check:

```bash
ollama list                        # are models pulled?
curl http://localhost:11434/api/tags   # is Ollama responding?
```

Start Ollama if needed:
```bash
ollama serve   # or: sudo systemctl start ollama
```

### "Startup timeout: 0/2 model services reachable after 60s"

The model took longer than `startup_timeout_seconds` to load. Either:
- Increase `startup_timeout_seconds` in `health_check:` config
- Or wait for the model to load, then run `lane status` manually

### Lane is DISABLED

`lane.enabled` is `false` in `config/workstation/local_lane.yaml`. Set it to `true`.

### Config file not found

`config/workstation/local_lane.yaml` does not exist. Copy the example:

```bash
cp config/workstation/local_lane.example.yaml config/workstation/local_lane.yaml
```

---

## What is not in scope for this lane

- **Automatic model download** — models must be pulled with `ollama pull` before use.
- **Multi-machine deployment** — the lane is single-machine only.
- **Automatic model selection** — Aider is called with a configured model; there is
  no dynamic model selection within the lane.
