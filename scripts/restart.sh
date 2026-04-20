#!/usr/bin/env bash
# =============================================================================
# WorkStation — restart.sh
# Stop the stack then bring it back up.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== WorkStation: restarting stack ==="
echo ""

echo "Step 1/2  Stopping..."
"${SCRIPT_DIR}/down.sh"

echo ""
echo "Step 2/2  Starting..."
"${SCRIPT_DIR}/up.sh"
