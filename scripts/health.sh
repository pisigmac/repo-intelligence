#!/usr/bin/env bash
# scripts/health.sh — Report health status of all Repo Intelligence services.
#
# Checks the API gateway plus each individual microservice that is exposed on
# the host, and prints a colour-coded summary table.
#
# Usage:
#   bash scripts/health.sh [--json] [--quiet] [-h|--help]
#
# Options:
#   --json    Emit machine-readable JSON instead of the human table.
#   --quiet   Suppress the table; exit 0 if all healthy, 1 if any unhealthy.
#   -h, --help  Show this help message and exit.
#
# Environment variables honoured:
#   REPO_INTEL_GATEWAY          Base URL for the API gateway (default: http://localhost:8000)
#   REPO_INTEL_HEALTH_TIMEOUT   Per-endpoint curl timeout in seconds (default: 5)
#
# Exit codes:
#   0  All checked endpoints are healthy.
#   1  One or more endpoints are unhealthy or unreachable.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

GATEWAY="${REPO_INTEL_GATEWAY:-http://localhost:8000}"
CURL_TIMEOUT="${REPO_INTEL_HEALTH_TIMEOUT:-5}"

JSON_OUTPUT=false
QUIET=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --json)    JSON_OUTPUT=true; shift ;;
    --quiet)   QUIET=true;       shift ;;
    -h|--help)
      sed -n '2,22p' "$0" | sed 's/^# //'
      exit 0
      ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

# ── Colour helpers (disabled when not a terminal) ────────────────────────────
if [[ -t 1 ]] && [[ "$JSON_OUTPUT" = false ]]; then
  GREEN='\033[0;32m'
  RED='\033[0;31m'
  YELLOW='\033[0;33m'
  RESET='\033[0m'
else
  GREEN='' RED='' YELLOW='' RESET=''
fi

# ── Endpoint definitions ─────────────────────────────────────────────────────
# Format: "Label|URL"
# Gateway proxies for microservices use the /health path through the gateway.
# Where a service is also port-forwarded to the host it is listed separately.
ENDPOINTS=(
  "API Gateway|${GATEWAY}/health"
  "Query Service (host:8080)|http://localhost:8080/health"
  "Approval Service (host:8081)|http://localhost:8081/health"
  "Dashboard UI (nginx:8090)|http://localhost:8090"
  "Qdrant|http://localhost:6333/healthz"
  "PostgreSQL (TCP)|tcp://localhost:5434"
)

# ── Health probe function ────────────────────────────────────────────────────
probe() {
  local url="$1"

  # TCP-only probe (PostgreSQL — no HTTP)
  if [[ "$url" == tcp://* ]]; then
    local host port
    host="${url#tcp://}"
    port="${host##*:}"
    host="${host%:*}"
    if command -v nc >/dev/null 2>&1; then
      nc -z -w "$CURL_TIMEOUT" "$host" "$port" >/dev/null 2>&1 && echo "200" || echo "000"
    else
      # Fallback: try bash /dev/tcp
      (echo > /dev/tcp/"$host"/"$port") >/dev/null 2>&1 && echo "200" || echo "000"
    fi
    return
  fi

  curl -s -o /dev/null -w '%{http_code}' \
    --connect-timeout "$CURL_TIMEOUT" \
    --max-time "$CURL_TIMEOUT" \
    "$url" 2>/dev/null || echo "000"
}

# ── Collect results ──────────────────────────────────────────────────────────
declare -a LABELS STATUSES CODES
ALL_HEALTHY=true

for entry in "${ENDPOINTS[@]}"; do
  label="${entry%%|*}"
  url="${entry##*|}"
  code=$(probe "$url")
  if [[ "$code" = "200" ]]; then
    status="healthy"
  else
    status="unhealthy"
    ALL_HEALTHY=false
  fi
  LABELS+=("$label")
  STATUSES+=("$status")
  CODES+=("$code")
done

# ── JSON output ──────────────────────────────────────────────────────────────
if [[ "$JSON_OUTPUT" = true ]]; then
  printf '{"timestamp":"%s","all_healthy":%s,"services":[' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    "$( [[ "$ALL_HEALTHY" = true ]] && echo true || echo false )"
  for i in "${!LABELS[@]}"; do
    [[ $i -gt 0 ]] && printf ','
    printf '{"name":"%s","status":"%s","http_code":"%s"}' \
      "${LABELS[$i]}" "${STATUSES[$i]}" "${CODES[$i]}"
  done
  printf ']}\n'
  "$ALL_HEALTHY" && exit 0 || exit 1
fi

# ── Quiet mode ───────────────────────────────────────────────────────────────
if [[ "$QUIET" = true ]]; then
  "$ALL_HEALTHY" && exit 0 || exit 1
fi

# ── Human-readable table ─────────────────────────────────────────────────────
echo ""
echo "=== Repo Intelligence — Service Health ==="
printf "  %-42s  %-10s  %s\n" "Service" "Status" "HTTP"
printf "  %-42s  %-10s  %s\n" "$(printf '%0.s-' {1..42})" "----------" "----"

for i in "${!LABELS[@]}"; do
  label="${LABELS[$i]}"
  status="${STATUSES[$i]}"
  code="${CODES[$i]}"
  if [[ "$status" = "healthy" ]]; then
    status_col="${GREEN}healthy${RESET}"
  else
    status_col="${RED}unhealthy${RESET}"
  fi
  printf "  %-42s  ${status_col}%-$((10 - ${#status}))s  %s\n" \
    "$label" "" "$code"
done

echo ""

# ── Docker Compose container status ─────────────────────────────────────────
if command -v docker-compose >/dev/null 2>&1; then
  if docker-compose ps -q >/dev/null 2>&1 && [[ -n $(docker-compose ps -q 2>/dev/null) ]]; then
    echo "=== Container Status ==="
    docker-compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null \
      || docker-compose ps
    echo ""
  fi
fi

# ── Summary ──────────────────────────────────────────────────────────────────
if [[ "$ALL_HEALTHY" = true ]]; then
  echo -e "${GREEN}All services healthy.${RESET}"
  exit 0
else
  echo -e "${RED}One or more services are unhealthy. Check logs with: make logs${RESET}"
  exit 1
fi
