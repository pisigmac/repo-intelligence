#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

GATEWAY="${REPO_INTEL_GATEWAY:-http://localhost:8000}"

echo "=== Container Status ==="
docker-compose ps

echo ""
echo "=== Gateway Health ==="
if curl -sf "$GATEWAY/health" > /dev/null 2>&1; then
  echo "Gateway: healthy ($GATEWAY/health)"
else
  echo "Gateway: not responding ($GATEWAY/health)"
fi
