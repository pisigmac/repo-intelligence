#!/usr/bin/env bash
# scripts/test.sh — Run unit tests and (optionally) integration tests.
#
# Usage:
#   bash scripts/test.sh [--unit-only] [--parser-only] [--utilities-only] [-h|--help]
#
# Options:
#   --unit-only        Run unit tests only; skip integration tests even if the stack is running.
#   --parser-only      Run only the parser-service unit test suite (fast, no Docker required).
#   --utilities-only   Run only the scripts/tests suite (bash + compose validation).
#   -h, --help         Show this help message and exit.
#
# Exit codes:
#   0  All selected tests passed.
#   1  One or more tests failed, or an unexpected option was supplied.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

UNIT_ONLY=false
PARSER_ONLY=false
UTILITIES_ONLY=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --unit-only)       UNIT_ONLY=true;       shift ;;
    --parser-only)     PARSER_ONLY=true;     shift ;;
    --utilities-only)  UTILITIES_ONLY=true;  shift ;;
    -h|--help)
      sed -n '2,16p' "$0" | sed 's/^# //'
      exit 0
      ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

# ── Parser-only shortcut ────────────────────────────────────────────────────
if [[ "$PARSER_ONLY" = true ]]; then
  echo "==> Running parser-service unit tests..."
  pytest services/parser/tests/ -v --confcutdir=services/parser/tests
  echo ""
  echo "Parser tests passed."
  exit 0
fi

# ── Utilities-only shortcut ─────────────────────────────────────────────────
if [[ "$UTILITIES_ONLY" = true ]]; then
  echo "==> Running scripts utility tests..."
  pytest scripts/tests/test_utilities.py -v --confcutdir=scripts/tests
  echo ""
  echo "Utility tests passed."
  exit 0
fi

# ── Unit test suite ─────────────────────────────────────────────────────────
echo "==> Running unit tests (all services)..."
pytest services/*/tests/ -v

echo ""
echo "==> Running parser-service unit tests..."
pytest services/parser/tests/ -v --confcutdir=services/parser/tests

echo ""
echo "==> Running scripts utility tests..."
pytest scripts/tests/test_utilities.py -v --confcutdir=scripts/tests

if [[ "$UNIT_ONLY" = true ]]; then
  echo ""
  echo "Unit tests passed. Skipping integration tests (--unit-only)."
  exit 0
fi

# ── Integration tests (requires running stack) ───────────────────────────────
if [[ -z $(docker-compose ps -q 2>/dev/null) ]]; then
  echo ""
  echo "WARNING: The Docker Compose stack does not appear to be running. Skipping integration tests." >&2
  echo "  Start it with: make start" >&2
  exit 1
fi

echo ""
echo "==> Waiting for API gateway to be healthy..."
bash "$SCRIPT_DIR/wait-for-healthy.sh"

echo ""
echo "==> Applying Phase 2 migrations..."
bash "$SCRIPT_DIR/apply-migrations.sh"

echo ""
echo "==> Running Phase 1 integration tests..."
bash "$SCRIPT_DIR/integration-test.sh"

echo ""
echo "==> Running Phase 2 integration tests..."
bash "$SCRIPT_DIR/phase2-integration-test.sh"

echo ""
echo "All tests passed."
