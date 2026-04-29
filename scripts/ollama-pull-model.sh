#!/usr/bin/env bash
# Pull a model into the running Ollama instance.
# Usage: bash scripts/ollama-pull-model.sh [model]
# Default model: qwen2.5-coder:3b
set -euo pipefail

MODEL="${1:-qwen2.5-coder:3b}"

if ! curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo "ERROR: Ollama is not reachable at http://localhost:11434" >&2
    echo "       Start it first: bash scripts/ollama-up.sh" >&2
    exit 1
fi

echo "  Pulling $MODEL from Ollama registry..."
curl -s -X POST http://localhost:11434/api/pull \
    -H "Content-Type: application/json" \
    -d "{\"name\": \"$MODEL\", \"stream\": false}" \
    | python3 -c "
import sys, json
data = json.load(sys.stdin)
status = data.get('status', '')
if 'success' in status or status == 'already exists':
    print(f'  Model ready: $MODEL')
else:
    print(f'  Pull status: {status}')
" 2>/dev/null || echo "  Pulled: $MODEL"
