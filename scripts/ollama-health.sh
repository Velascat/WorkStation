#!/usr/bin/env bash
# Check health of the local Ollama instance.
# Usage: bash scripts/ollama-health.sh [base_url]
# Default base_url: http://localhost:11434
# Exit code: 0 = healthy, 1 = unreachable
set -euo pipefail

BASE_URL="${1:-http://localhost:11434}"

echo "=== WorkStation: Ollama health check ==="
echo "  Endpoint: $BASE_URL"

if curl -sf "$BASE_URL/api/tags" >/dev/null 2>&1; then
    echo "  Status:   REACHABLE"
    echo ""
    echo "  Available models:"
    curl -s "$BASE_URL/api/tags" \
        | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    models = data.get('models', [])
    if not models:
        print('    (no models pulled yet)')
    for m in models:
        name = m.get('name', '?')
        size = m.get('size', 0)
        size_gb = size / 1024**3
        print(f'    {name:<30}  {size_gb:.1f} GB')
except Exception as e:
    print(f'    (could not parse model list: {e})')
" 2>/dev/null || echo "    (could not list models)"
    echo ""
    exit 0
else
    echo "  Status:   UNREACHABLE"
    echo ""
    echo "  Start Ollama: bash scripts/ollama-up.sh"
    echo "  Or:           ollama serve"
    echo ""
    exit 1
fi
