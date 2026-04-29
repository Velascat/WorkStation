#!/usr/bin/env bash
# Start the Ollama container for the aider_local lane.
# Usage: bash scripts/ollama-up.sh [model]
# Default model: qwen2.5-coder:3b
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$REPO_ROOT/compose/docker-compose.local-ai.yml"
MODEL="${1:-qwen2.5-coder:3b}"

echo "=== WorkStation: starting Ollama ==="
docker compose -f "$COMPOSE_FILE" up -d

echo "  Waiting for Ollama to be ready..."
for i in $(seq 1 30); do
    if curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
        echo "  Ollama is ready."
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "  ERROR: Ollama did not become ready after 30s." >&2
        exit 1
    fi
    sleep 1
done

echo "  Pulling model: $MODEL"
bash "$SCRIPT_DIR/ollama-pull-model.sh" "$MODEL"

echo ""
echo "  Lane is ready. Run: workstation lane status aider_local"
