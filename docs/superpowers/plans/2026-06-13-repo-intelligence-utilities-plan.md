# Repo Intelligence Platform — Local Dev Utilities Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a set of self-contained Bash utilities in `scripts/` for starting, stopping, restarting, inspecting, resetting, migrating, and logging the local Repo Intelligence stack, plus Makefile shortcuts and a `scripts/utilities.md` guide.

**Architecture:** Each utility is an independent Bash script that computes the repo root, uses `docker-compose` and `curl`, and follows the same `set -euo pipefail` safety conventions. A reusable `wait-for-healthy.sh` helper blocks until the API gateway responds, and destructive commands require confirmation unless `-y`/`--force` is passed.

**Tech Stack:** Bash, Docker Compose, curl, POSIX tools, pytest for lightweight existence/syntax tests.

---

## File map

| File | Responsibility |
|---|---|
| `scripts/wait-for-healthy.sh` | Poll gateway `/health` until ready or timeout. |
| `scripts/apply-migrations.sh` | Apply `migrations/phase2.sql` to the running Postgres container. |
| `scripts/start_all.sh` | Build and start services, wait for readiness, apply migrations, optionally seed. |
| `scripts/stop_all.sh` | Stop and remove the stack with optional confirmation. |
| `scripts/restart_all.sh` | Stop then start the stack. |
| `scripts/status_all.sh` | Show container status and gateway health. |
| `scripts/logs_all.sh` | Tail aggregated or per-service logs. |
| `scripts/reset_all.sh` | Stop, remove volumes, and recreate a fresh environment. |
| `scripts/utilities.md` | User guide for the utilities. |
| `Makefile` | Add convenience targets that delegate to the scripts. |
| `scripts/tests/test_utilities.py` | Lightweight pytest checks that scripts exist and have valid Bash syntax. |

---

### Task 1: Create `wait-for-healthy.sh`

**Files:**
- Create: `scripts/wait-for-healthy.sh`

- [ ] **Step 1: Write the script**

```bash
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
```

- [ ] **Step 2: Make it executable**

Run: `chmod +x scripts/wait-for-healthy.sh`

- [ ] **Step 3: Smoke test**

Run: `bash scripts/wait-for-healthy.sh`
Expected: fails with timeout if stack is down; prints progress messages.

- [ ] **Step 4: Commit**

```bash
git add scripts/wait-for-healthy.sh
git commit -m "feat(utilities): add wait-for-healthy helper"
```

---

### Task 2: Create `apply-migrations.sh`

**Files:**
- Create: `scripts/apply-migrations.sh`

- [ ] **Step 1: Write the script**

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

echo "Applying Phase 2 migrations..."
docker-compose exec -T postgres psql -U repo -d repo_intelligence < migrations/phase2.sql

echo "Migrations applied."
```

- [ ] **Step 2: Make it executable**

Run: `chmod +x scripts/apply-migrations.sh`

- [ ] **Step 3: Syntax check**

Run: `bash -n scripts/apply-migrations.sh`

- [ ] **Step 4: Commit**

```bash
git add scripts/apply-migrations.sh
git commit -m "feat(utilities): add apply-migrations script"
```

---

### Task 3: Create `start_all.sh`

**Files:**
- Create: `scripts/start_all.sh`

- [ ] **Step 1: Write the script**

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

SEED=false
BUILD=true

while [[ $# -gt 0 ]]; do
  case "$1" in
    --seed) SEED=true; shift ;;
    --no-build) BUILD=false; shift ;;
    -h|--help)
      echo "Usage: $0 [--seed] [--no-build]"
      exit 0
      ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

if [ "$BUILD" = true ]; then
  echo "Building and starting services..."
  docker-compose up -d --build
else
  echo "Starting services..."
  docker-compose up -d
fi

echo "Waiting for Kafka topics to initialize..."
sleep 10

echo "Applying Phase 2 migrations..."
bash "$SCRIPT_DIR/apply-migrations.sh"

echo "Waiting for API gateway to be healthy..."
bash "$SCRIPT_DIR/wait-for-healthy.sh"

if [ "$SEED" = true ]; then
  echo "Seeding test repository..."
  bash "$SCRIPT_DIR/seed-data.sh"
fi

echo ""
echo "Stack is ready."
echo "Gateway: http://localhost:8000"
```

- [ ] **Step 2: Make it executable**

Run: `chmod +x scripts/start_all.sh`

- [ ] **Step 3: Smoke test syntax**

Run: `bash -n scripts/start_all.sh`
Expected: no output (success).

- [ ] **Step 4: Commit**

```bash
git add scripts/start_all.sh
git commit -m "feat(utilities): add start_all script"
```

---

### Task 4: Create `stop_all.sh`

**Files:**
- Create: `scripts/stop_all.sh`

- [ ] **Step 1: Write the script**

```bash
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

if [ "$FORCE" = false ]; then
  read -rp "Stop and remove the Repo Intelligence stack? [y/N] " answer
  if [[ ! "$answer" =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 2
  fi
fi

echo "Stopping stack..."
docker-compose down

echo "Stack stopped."
```

- [ ] **Step 2: Make it executable**

Run: `chmod +x scripts/stop_all.sh`

- [ ] **Step 3: Syntax check**

Run: `bash -n scripts/stop_all.sh`

- [ ] **Step 4: Commit**

```bash
git add scripts/stop_all.sh
git commit -m "feat(utilities): add stop_all script"
```

---

### Task 5: Create `restart_all.sh`

**Files:**
- Create: `scripts/restart_all.sh`

- [ ] **Step 1: Write the script**

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Restarting Repo Intelligence stack..."
bash "$SCRIPT_DIR/stop_all.sh" "$@"
bash "$SCRIPT_DIR/start_all.sh"
echo "Restart complete."
```

- [ ] **Step 2: Make it executable**

Run: `chmod +x scripts/restart_all.sh`

- [ ] **Step 3: Syntax check**

Run: `bash -n scripts/restart_all.sh`

- [ ] **Step 4: Commit**

```bash
git add scripts/restart_all.sh
git commit -m "feat(utilities): add restart_all script"
```

---

### Task 6: Create `status_all.sh`

**Files:**
- Create: `scripts/status_all.sh`

- [ ] **Step 1: Write the script**

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

GATEWAY="${REPO_INTEL_GATEWAY:-http://localhost:8000}"

echo "=== Container Status ==="
docker-compose ps

echo ""
echo "=== Gateway Health ==="
if curl -sf "$GATEWAY/health" > /dev/null 2>&1; then
  echo "Gateway: healthy ($GATEWAY/health)"
else
  echo "Gateway: not responding ($GATEWAY/health)"
fi
```

- [ ] **Step 2: Make it executable**

Run: `chmod +x scripts/status_all.sh`

- [ ] **Step 3: Syntax check**

Run: `bash -n scripts/status_all.sh`

- [ ] **Step 4: Commit**

```bash
git add scripts/status_all.sh
git commit -m "feat(utilities): add status_all script"
```

---

### Task 7: Create `logs_all.sh`

**Files:**
- Create: `scripts/logs_all.sh`

- [ ] **Step 1: Write the script**

```bash
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
```

- [ ] **Step 2: Make it executable**

Run: `chmod +x scripts/logs_all.sh`

- [ ] **Step 3: Syntax check**

Run: `bash -n scripts/logs_all.sh`

- [ ] **Step 4: Commit**

```bash
git add scripts/logs_all.sh
git commit -m "feat(utilities): add logs_all script"
```

---

### Task 8: Create `reset_all.sh`

**Files:**
- Create: `scripts/reset_all.sh`

- [ ] **Step 1: Write the script**

```bash
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

if [ "$FORCE" = false ]; then
  echo "WARNING: This will delete all Postgres, Qdrant, and repo-storage volumes."
  read -rp "Reset the Repo Intelligence environment? [y/N] " answer
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
```

- [ ] **Step 2: Make it executable**

Run: `chmod +x scripts/reset_all.sh`

- [ ] **Step 3: Syntax check**

Run: `bash -n scripts/reset_all.sh`

- [ ] **Step 4: Commit**

```bash
git add scripts/reset_all.sh
git commit -m "feat(utilities): add reset_all script"
```

---

### Task 9: Update `Makefile`

**Files:**
- Modify: `Makefile`

- [ ] **Step 1: Read existing Makefile**

File currently contains `.PHONY: build up down logs test seed clean proto` and targets.

- [ ] **Step 2: Add new targets**

Replace the first line with:

```makefile
.PHONY: build up down logs test seed clean proto start stop restart status reset migrate wait
```

Insert before the existing `build:` target:

```makefile
start:
	bash scripts/start_all.sh

stop:
	bash scripts/stop_all.sh

restart:
	bash scripts/restart_all.sh

status:
	bash scripts/status_all.sh

reset:
	bash scripts/reset_all.sh

migrate:
	bash scripts/apply-migrations.sh

wait:
	bash scripts/wait-for-healthy.sh
```

Leave existing targets unchanged.

- [ ] **Step 3: Syntax check**

Run: `make -n start`
Expected: prints `bash scripts/start_all.sh`.

- [ ] **Step 4: Commit**

```bash
git add Makefile
git commit -m "feat(utilities): add Makefile shortcuts for new scripts"
```

---

### Task 10: Create `scripts/utilities.md`

**Files:**
- Create: `scripts/utilities.md`

- [ ] **Step 1: Write the guide**

```markdown
# Repo Intelligence Local Development Utilities

These scripts wrap `docker-compose` commands to make local development easier. They are intended for **local use only**.

## Quick start

```bash
# Start everything, apply migrations, and seed the test repo
make start
# or
bash scripts/start_all.sh --seed

# Check status
make status

# Tail logs
make logs

# Stop everything
make stop
# or with confirmation bypass
bash scripts/stop_all.sh -y
```

## Scripts

| Script | Purpose | Example |
|---|---|---|
| `start_all.sh` | Build and start the stack, apply migrations, optionally seed. | `bash scripts/start_all.sh --seed` |
| `stop_all.sh` | Stop and remove the stack. Prompts for confirmation unless `-y`. | `bash scripts/stop_all.sh --force` |
| `restart_all.sh` | Stop then start the stack. | `bash scripts/restart_all.sh -y` |
| `status_all.sh` | Show container status and gateway health. | `bash scripts/status_all.sh` |
| `logs_all.sh` | Tail aggregated or per-service logs. | `bash scripts/logs_all.sh -s execution-service -n 50` |
| `apply-migrations.sh` | Apply `migrations/phase2.sql`. | `bash scripts/apply-migrations.sh` |
| `reset_all.sh` | Stop, remove volumes, and recreate a fresh environment. | `bash scripts/reset_all.sh -y` |
| `wait-for-healthy.sh` | Block until the gateway health endpoint returns 200. | `bash scripts/wait-for-healthy.sh` |

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `REPO_INTEL_GATEWAY` | `http://localhost:8000` | URL of the API gateway health endpoint. |
| `REPO_INTEL_START_TIMEOUT` | `120` | Seconds to wait for the gateway to become healthy. |
| `REPO_INTEL_HEALTH_INTERVAL` | `2` | Seconds between health polls. |
| `COMPOSE_FILE` | `docker-compose.yml` | Standard Docker Compose variable (handled by `docker-compose`). |

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | General failure (Docker/Compose error, health timeout, unknown option) |
| `2` | Cancelled by user |

## Troubleshooting

- **Docker not running:** Scripts fail fast with an error from `docker-compose`. Start Docker first.
- **Gateway timeout:** Increase `REPO_INTEL_START_TIMEOUT`. Check service logs with `make logs`.
- **Port conflicts:** Ensure ports `8000`, `8080`, `8081`, `5432`, `6333`, `9092`, and `19092` are free.
- **Migrations fail:** Verify the `postgres` container is healthy: `docker-compose ps`.
```

- [ ] **Step 2: Commit**

```bash
git add scripts/utilities.md
git commit -m "docs(utilities): add utilities guide"
```

---

### Task 11: Add lightweight pytest tests

**Files:**
- Create: `scripts/tests/test_utilities.py`

- [ ] **Step 1: Write the tests**

```python
import pathlib
import subprocess

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"

UTILITIES = [
    "wait-for-healthy.sh",
    "start_all.sh",
    "stop_all.sh",
    "restart_all.sh",
    "status_all.sh",
    "logs_all.sh",
    "apply-migrations.sh",
    "reset_all.sh",
]


def test_utility_scripts_exist():
    for name in UTILITIES:
        path = SCRIPTS_DIR / name
        assert path.exists(), f"Missing utility script: {path}"


def test_utility_scripts_are_executable():
    for name in UTILITIES:
        path = SCRIPTS_DIR / name
        assert path.stat().st_mode & 0o111, f"Script is not executable: {path}"


def test_utility_scripts_have_valid_bash_syntax():
    for name in UTILITIES:
        path = SCRIPTS_DIR / name
        result = subprocess.run(
            ["bash", "-n", str(path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Syntax error in {path}: {result.stderr}"
```

- [ ] **Step 2: Run the tests**

Run: `pytest scripts/tests/test_utilities.py -v`
Expected: all tests pass.

- [ ] **Step 3: Commit**

```bash
git add scripts/tests/test_utilities.py
git commit -m "test(utilities): add syntax and existence tests for utility scripts"
```

---

### Task 12: Final verification

- [ ] **Step 1: Run the full unit test suite**

Run: `make test`
Expected: existing tests still pass and new utility tests pass.

- [ ] **Step 2: Verify Makefile shortcuts**

Run: `make -n start stop restart status reset migrate wait logs`
Expected: each prints the corresponding `bash scripts/...` command without error.

- [ ] **Step 3: Optionally start the stack (manual)**

Run: `bash scripts/start_all.sh --seed`
Expected: services start, migrations apply, gateway health returns 200, test repo is ingested.

- [ ] **Step 4: Commit any final changes**

```bash
git add -A
git commit -m "feat(utilities): complete local dev utility scripts" || true
```

---

## Spec coverage

| Spec requirement | Implementing task |
|---|---|
| `wait-for-healthy.sh` | Task 1 |
| `apply-migrations.sh` | Task 2 |
| `start_all.sh` — start, wait, migrate, optional seed | Task 3 |
| `stop_all.sh` — confirmation / `-y` | Task 4 |
| `restart_all.sh` | Task 5 |
| `status_all.sh` | Task 6 |
| `logs_all.sh` | Task 7 |
| `reset_all.sh` — destructive confirmation / recreate | Task 8 |
| Makefile shortcuts | Task 9 |
| `scripts/utilities.md` | Task 10 |
| Lightweight tests | Task 11 |
