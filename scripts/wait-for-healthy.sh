#!/usr/bin/env bash
set -euo pipefail

GATEWAY="${REPO_INTEL_GATEWAY:-http://localhost:8000}"
TIMEOUT="${REPO_INTEL_START_TIMEOUT:-120}"
INTERVAL="${REPO_INTEL_HEALTH_INTERVAL:-2}"

START=$(date +%s)
END=$((START + TIMEOUT))

echo "Waiting for gateway at $GATEWAY/health (timeout: ${TIMEOUT}s)..."

while [ "$(date +%s)" -lt "$END" ]; do
  if curl -sf "$GATEWAY/health" > /dev/null 2>&1; then
    echo "Gateway is healthy."
    exit 0
  fi
  sleep "$INTERVAL"
done

echo "ERROR: Gateway did not become healthy within ${TIMEOUT}s."
exit 1
