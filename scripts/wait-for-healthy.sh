#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

GATEWAY="${REPO_INTEL_GATEWAY:-http://localhost:8000}"
TIMEOUT="${REPO_INTEL_START_TIMEOUT:-120}"
INTERVAL="${REPO_INTEL_HEALTH_INTERVAL:-2}"

if ! [[ "$TIMEOUT" =~ ^[0-9]+$ ]] || ! [[ "$INTERVAL" =~ ^[0-9]+$ ]]; then
  echo "ERROR: REPO_INTEL_START_TIMEOUT and REPO_INTEL_HEALTH_INTERVAL must be non-negative integers." >&2
  exit 1
fi

START=$(date +%s)
END=$((START + TIMEOUT))

echo "Waiting for gateway at $GATEWAY/health (timeout: ${TIMEOUT}s)..."

last_status="unknown"
while [ "$(date +%s)" -lt "$END" ]; do
  last_status=$(curl -s -o /dev/null -w '%{http_code}' \
    --connect-timeout 2 --max-time "$INTERVAL" \
    "$GATEWAY/health" || true)

  if [ "$last_status" = "200" ]; then
    echo "Gateway is healthy."
    exit 0
  fi

  sleep "$INTERVAL"
done

echo "ERROR: Gateway did not become healthy within ${TIMEOUT}s (last HTTP status: ${last_status})."
exit 1
