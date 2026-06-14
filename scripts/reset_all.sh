#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

FORCE=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    -y|--force) FORCE=true; shift ;;
    -h|--help)
      echo "Usage: $0 [-y|--force]"
      exit 0
      ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

if [[ "$FORCE" = false ]]; then
  echo "WARNING: This will delete all Postgres, Qdrant, and repo-storage volumes."
  if ! read -rp "Reset the Repo Intelligence environment? [y/N] " answer; then
    echo "No input received; cancelled."
    exit 2
  fi
  if [[ ! "$answer" =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 2
  fi
fi

echo "Stopping and removing volumes..."
docker-compose down -v

echo "Starting fresh environment..."
bash "$SCRIPT_DIR/start_all.sh"

echo "Reset complete."
