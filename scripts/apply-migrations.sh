#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

echo "Applying Phase 2 migrations..."
docker-compose exec -T postgres psql -U repo -d repo_intelligence < migrations/phase2.sql

echo "Migrations applied."
