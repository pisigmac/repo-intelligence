#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Restarting Repo Intelligence stack..."
bash "$SCRIPT_DIR/stop_all.sh" "$@"
bash "$SCRIPT_DIR/start_all.sh"
echo "Restart complete."
