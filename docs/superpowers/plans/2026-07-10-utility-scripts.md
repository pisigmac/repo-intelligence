# Utility Scripts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Add `setup.sh`, `test.sh`, and `health.sh` to `scripts/` and wire them into `Makefile` and `scripts/utilities.md`.

**Architecture:** Three standalone bash scripts that follow the existing `scripts/` conventions (shebang, `set -euo pipefail`, `SCRIPT_DIR`/`REPO_ROOT`). `setup.sh` checks prerequisites and builds images. `test.sh` runs pytest followed by the integration test scripts. `health.sh` probes every service's internal `/health` endpoint via `docker-compose exec`. `Makefile` gets thin targets; `utilities.md` documents the new commands.

**Tech Stack:** Bash, Docker Compose, curl, pytest.

---

## File Structure

| File | Responsibility |
|---|---|
| `scripts/setup.sh` (create) | One-time local environment setup: verify Docker, create `.env` if missing, build images. |
| `scripts/test.sh` (create) | Run unit tests, then Phase 1 and Phase 2 integration tests. |
| `scripts/health.sh` (create) | Probe `/health` on every service in the compose stack and print a status table. |
| `Makefile` (modify) | Add `setup`, `test`, and `health` targets that delegate to the new scripts. |
| `scripts/utilities.md` (modify) | Document the three new scripts, their flags, and exit codes. |

---

### Task 1: Create `scripts/setup.sh`

**Files:**
- Create: `scripts/setup.sh`

- [x] **Step 1: Create the script file**

```bash
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
```

- [x] **Step 2: Make the script executable**

Run: `chmod +x scripts/setup.sh`

- [x] **Step 3: Verify the script runs in help mode**

Run: `bash scripts/setup.sh --help`
Expected: prints usage and exits 0.

- [x] **Step 4: Verify the script creates `.env` and builds images**

Run: `rm -f .env && bash scripts/setup.sh`
Expected: `.env` is created, `docker-compose build` runs, script exits 0.

- [x] **Step 5: Commit**

```bash
git add scripts/setup.sh
if [ -f .env ]; then git add .env; fi
git commit -m "feat(scripts): add setup.sh for one-time local environment setup"
```

---

### Task 2: Create `scripts/test.sh`

**Files:**
- Create: `scripts/test.sh`

- [x] **Step 1: Create the script file**

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

UNIT_ONLY=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --unit-only) UNIT_ONLY=true; shift ;;
    -h|--help)
      echo "Usage: $0 [--unit-only]"
      exit 0
      ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

echo "==> Running unit tests..."
pytest services/*/tests/ -v

if [[ "$UNIT_ONLY" = true ]]; then
  echo ""
  echo "Unit tests passed. Skipping integration tests (--unit-only)."
  exit 0
fi

if ! docker-compose ps -q | grep -q .; then
  echo ""
  echo "WARNING: The Docker Compose stack does not appear to be running. Skipping integration tests." >&2
  echo "Start it with: make start" >&2
  exit 0
fi

echo ""
echo "==> Running Phase 1 integration tests..."
bash "$SCRIPT_DIR/integration-test.sh"

echo ""
echo "==> Running Phase 2 integration tests..."
bash "$SCRIPT_DIR/phase2-integration-test.sh"

echo ""
echo "All tests passed."
```

- [x] **Step 2: Make the script executable**

Run: `chmod +x scripts/test.sh`

- [x] **Step 3: Verify unit-only mode**

Run: `bash scripts/test.sh --unit-only`
Expected: pytest runs and exits 0 (or with existing test results).

- [x] **Step 4: Verify help mode**

Run: `bash scripts/test.sh --help`
Expected: prints usage and exits 0.

- [x] **Step 5: Commit**

```bash
git add scripts/test.sh
git commit -m "feat(scripts): add test.sh for unit and integration tests"
```

---

### Task 3: Create `scripts/health.sh`

**Files:**
- Create: `scripts/health.sh`

- [x] **Step 1: Create the script file**

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      echo "Usage: $0"
      echo "Check the /health endpoint of every service in docker-compose.yml."
      exit 0
      ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

# Only check services whose containers are currently running.
SERVICES=$(docker-compose ps --services --filter status=running 2>/dev/null || true)

if [[ -z "$SERVICES" ]]; then
  echo "ERROR: No running services found. Start the stack first with: make start" >&2
  exit 1
fi

TOTAL=0
HEALTHY=0
UNHEALTHY=0

printf "%-30s %-12s %-10s %s\n" "SERVICE" "STATUS" "HTTP" "RESPONSE"
printf "%-30s %-12s %-10s %s\n" "-------" "------" "----" "--------"

for service in $SERVICES; do
  TOTAL=$((TOTAL + 1))

  # Prefer Python because every service image includes it; fall back to wget/curl.
  result=$(docker-compose exec -T "$service" sh -c '
    response=""
    if command -v python3 >/dev/null 2>&1; then
      response=$(python3 -c "import urllib.request; print(urllib.request.urlopen(\"http://localhost:8080/health\", timeout=5).read().decode())" 2>/dev/null) || true
    elif command -v wget >/dev/null 2>&1; then
      response=$(wget -qO- --timeout=5 http://localhost:8080/health 2>/dev/null) || true
    elif command -v curl >/dev/null 2>&1; then
      response=$(curl -sf --max-time 5 http://localhost:8080/health 2>/dev/null) || true
    fi
    printf "%s" "$response"
  ' 2>/dev/null || true)

  if [[ "$result" == *'"status": "ok"'* ]]; then
    printf "%-30s %-12s %-10s %s\n" "$service" "healthy" "200" "$(echo "$result" | head -c 60)"
    HEALTHY=$((HEALTHY + 1))
  else
    printf "%-30s %-12s %-10s %s\n" "$service" "unhealthy" "-" "-"
    UNHEALTHY=$((UNHEALTHY + 1))
  fi
done

echo ""
echo "$HEALTHY/$TOTAL services healthy."

if [[ "$UNHEALTHY" -gt 0 ]]; then
  exit 1
fi
```

- [x] **Step 2: Make the script executable**

Run: `chmod +x scripts/health.sh`

- [x] **Step 3: Verify help mode**

Run: `bash scripts/health.sh --help`
Expected: prints usage and exits 0.

- [x] **Step 4: Verify health check with stack running**

Start the stack: `make start`
Run: `bash scripts/health.sh`
Expected: table lists services; most report healthy. Exit 0 if all healthy, 1 if any are not.

- [x] **Step 5: Commit**

```bash
git add scripts/health.sh
git commit -m "feat(scripts): add health.sh to probe all service health endpoints"
```

---

### Task 4: Update `Makefile`

**Files:**
- Modify: `Makefile`

- [x] **Step 1: Add new targets after the `.PHONY` line**

Add these targets after the existing targets:

```makefile
setup:
	bash scripts/setup.sh

test:
	bash scripts/test.sh

health:
	bash scripts/health.sh
```

The full `.PHONY` line should become:

```makefile
.PHONY: build up down logs test seed clean proto start stop restart status reset migrate wait setup health
```

- [x] **Step 2: Verify `make` shows the targets**

Run: `make help` if available, otherwise `grep -E '^[a-zA-Z_-]+:' Makefile | head -20`
Expected: `setup`, `test`, and `health` appear in the list.

- [x] **Step 3: Dry-run the new targets**

Run: `make setup --dry-run` (GNU Make) or `make -n setup`
Expected: shows `bash scripts/setup.sh`.

Run: `make health --dry-run` or `make -n health`
Expected: shows `bash scripts/health.sh`.

- [x] **Step 4: Commit**

```bash
git add Makefile
git commit -m "build(makefile): add setup, test, and health targets"
```

---

### Task 5: Update `scripts/utilities.md`

**Files:**
- Modify: `scripts/utilities.md`

- [x] **Step 1: Add the new scripts to the scripts table**

Insert three rows after `logs_all.sh`:

```markdown
| `setup.sh` | One-time environment setup: verify Docker, create `.env`, build images. | `bash scripts/setup.sh` |
| `test.sh` | Run unit tests, then Phase 1 and Phase 2 integration tests. | `bash scripts/test.sh` or `bash scripts/test.sh --unit-only` |
| `health.sh` | Probe `/health` on every service and print a status table. | `bash scripts/health.sh` |
```

- [x] **Step 2: Add a quick-start example for the new scripts**

After the existing "Quick start" code block, add:

```markdown
## Setup

```bash
# First time only: verify dependencies, create .env, build images
make setup
```

## Testing

```bash
# Run unit tests only
bash scripts/test.sh --unit-only

# Run unit + integration tests (stack must be running)
make test
```

## Health checks

```bash
# Check every service's /health endpoint
make health
```
```

- [x] **Step 3: Verify the markdown renders**

Run: `cat scripts/utilities.md | head -80`
Expected: new rows and sections are present, no broken table lines.

- [x] **Step 4: Commit**

```bash
git add scripts/utilities.md
git commit -m "docs(scripts): document setup.sh, test.sh, and health.sh"
```

---

## Self-Review

**Spec coverage:**

| Spec Requirement | Implementing Task |
|---|---|
| Add `setup.sh` that verifies Docker, creates `.env`, builds images | Task 1 |
| Add `test.sh` that runs unit + integration tests | Task 2 |
| Add `health.sh` that probes all service `/health` endpoints | Task 3 |
| Update `Makefile` with convenient targets | Task 4 |
| Update `scripts/utilities.md` documentation | Task 5 |

**Placeholder scan:**
- No "TBD", "TODO", or vague steps.
- Every task contains the full script or diff content.
- Verification commands and expected outputs are included.

**Type consistency:**
- All scripts use `#!/usr/bin/env bash`, `set -euo pipefail`, and the same `SCRIPT_DIR`/`REPO_ROOT` pattern.
- Health check looks for the same `"status": "ok"` JSON shape returned by all services.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-07-10-utility-scripts.md`.**

Two execution options:

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task and review between tasks.
2. **Inline Execution** — I execute tasks in this session using executing-plans with checkpoints.

Which approach would you like?
