#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

show_help() {
  echo "Usage: $0 [-h|--help]"
  echo ""
  echo "One-time environment setup for local development:"
  echo "  - Verify Docker and Docker Compose are installed"
  echo "  - Create .env with local defaults if it does not exist"
  echo "  - Build Docker images"
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) show_help ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

echo "==> Repo Intelligence setup"

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker is not installed or not in PATH." >&2
  exit 1
fi

if ! command -v docker-compose >/dev/null 2>&1; then
  echo "ERROR: docker-compose is not installed or not in PATH." >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "ERROR: Docker daemon is not running or you lack permissions." >&2
  exit 1
fi

if [[ ! -f ".env" ]]; then
  echo "==> Creating .env with local defaults..."
  cat > .env <<EOF
# Local development defaults for Repo Intelligence
OPENAI_API_KEY=
CORS_ORIGINS=http://localhost:8090
EOF
  echo "    .env created. Edit it if you need to set OPENAI_API_KEY."
else
  echo "==> .env already exists, skipping creation."
fi

echo "==> Building Docker images..."
docker-compose build

echo ""
echo "Setup complete. Start the stack with:"
echo "  make start"
