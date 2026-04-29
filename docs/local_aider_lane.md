# Local Aider Lane — Setup & Operation

The `aider_local` lane runs [Aider](https://aider.chat/) against a local [Ollama](https://ollama.com/) inference server. It is CPU-only, costs nothing per execution, and is designed for low-risk tasks on machines with 8 GB RAM.

## Architecture

```
OperatorConsole  →  [queue task, lane_hint=aider_local]
SwitchBoard      →  lane=aider_local, backend=aider_local
OperationsCenter →  AiderLocalBackendAdapter.execute()
                        aider --model ollama/qwen2.5-coder:3b
                              --api-base http://localhost:11434
                              --yes-always
                              --message-file /tmp/<run_id>.txt
WorkStation      →  provisions Ollama + model
```

## Quick start

1. **Copy the config template:**

   ```bash
   cp config/workstation/local_lane.example.yaml config/workstation/local_lane.yaml
   ```

2. **Enable the lane** — edit `config/workstation/local_lane.yaml`:

   ```yaml
   lane:
     enabled: true
   ```

3. **Start Ollama** (Docker):

   ```bash
   bash scripts/ollama-up.sh
   ```

   Or if Ollama is already installed locally:

   ```bash
   ollama serve &
   ollama pull qwen2.5-coder:3b
   ```

4. **Verify the lane is ready:**

   ```bash
   python -m workstation_cli lane doctor aider_local
   python -m workstation_cli lane status aider_local
   ```

## CLI commands

| Command | Description |
|---------|-------------|
| `workstation lane start aider_local` | Start managed model services |
| `workstation lane stop aider_local` | Stop managed model services |
| `workstation lane status aider_local` | Show state and model health |
| `workstation lane health aider_local` | Live endpoint check |
| `workstation lane doctor aider_local` | Full pre-flight diagnostic |

## Model recommendations (8 GB RAM, CPU-only)

| Model | RAM | Use |
|-------|-----|-----|
| `qwen2.5-coder:3b` | ~2 GB | Default — best code quality at this size |
| `qwen2.5-coder:1.5b` | ~1 GB | Faster, lighter |

## Docker setup

The provided compose file runs Ollama in a container with CPU-only mode:

```bash
docker compose -f compose/docker-compose.local-ai.yml up -d
bash scripts/ollama-pull-model.sh qwen2.5-coder:3b
```

## Suitable task classes

The `aider_local` lane is intended for:

- `lint_fix` — formatting, linting, style fixes
- `simple_edit` — small, bounded changes
- `documentation` — docstrings, README updates
- `test_fix` — fixing broken tests (not writing new ones)

Higher-risk tasks (refactors, features, bug fixes in critical paths) route to the `claude_cli` lane automatically via SwitchBoard.

## Health check script

```bash
bash scripts/ollama-health.sh
```

Exit code 0 = Ollama reachable; 1 = unreachable.
