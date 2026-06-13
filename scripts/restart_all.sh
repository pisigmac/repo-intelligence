#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

STOP_ARGS=()
START_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    -y|--force)
      STOP_ARGS+=("$1")
      shift
      ;;
    --seed|--no-build)
      START_ARGS+=("$1")
      shift
      ;;
    -h|--help)
      echo "Usage: $0 [-y|--force] [--seed] [--no-build]"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

echo "Restarting Repo Intelligence stack..."
bash "$SCRIPT_DIR/stop_all.sh" "${STOP_ARGS[@]}"
bash "$SCRIPT_DIR/start_all.sh" "${START_ARGS[@]}"
echo "Restart complete."
