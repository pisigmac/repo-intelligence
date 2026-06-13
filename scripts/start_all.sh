#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

SEED=false
BUILD=true

while [[ $# -gt 0 ]]; do
  case "$1" in
    --seed) SEED=true; shift ;;
    --no-build) BUILD=false; shift ;;
    -h|--help)
      echo "Usage: $0 [--seed] [--no-build]"
      exit 0
      ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

if [ "$BUILD" = true ]; then
  echo "Building and starting services..."
  docker-compose up -d --build
else
  echo "Starting services..."
  docker-compose up -d
fi

echo "Waiting for Kafka topics to initialize..."
sleep 10

echo "Applying Phase 2 migrations..."
bash "$SCRIPT_DIR/apply-migrations.sh"

echo "Waiting for API gateway to be healthy..."
bash "$SCRIPT_DIR/wait-for-healthy.sh"

if [ "$SEED" = true ]; then
  echo "Seeding test repository..."
  bash "$SCRIPT_DIR/seed-data.sh"
fi

echo ""
echo "Stack is ready."
echo "Gateway: http://localhost:8000"
