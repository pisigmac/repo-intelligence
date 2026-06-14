#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

SERVICE=""
LINES=100
FOLLOW=true

while [[ $# -gt 0 ]]; do
  case "$1" in
    -s|--service) SERVICE="$2"; shift 2 ;;
    -n|--lines) LINES="$2"; shift 2 ;;
    --no-follow) FOLLOW=false; shift ;;
    -h|--help)
      echo "Usage: $0 [-s <service>] [-n <lines>] [--no-follow]"
      exit 0
      ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

FLAGS=()
FLAGS+=("--tail=$LINES")
if [ "$FOLLOW" = true ]; then
  FLAGS+=("-f")
fi

if [ -n "$SERVICE" ]; then
  echo "Tailing logs for $SERVICE..."
  docker-compose logs "${FLAGS[@]}" "$SERVICE"
else
  echo "Tailing all logs..."
  docker-compose logs "${FLAGS[@]}"
fi
