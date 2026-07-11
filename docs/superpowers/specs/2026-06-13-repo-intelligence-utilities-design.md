# Repo Intelligence Platform — Local Dev Utilities Design

**Date:** 2026-06-13  
**Author:** Kimi Code  
**Status:** Draft (pending implementation plan)

## 1. Purpose

Operating the Repo Intelligence Platform locally currently requires several manual `docker-compose` and `psql` commands (build, up, wait, migrate, seed, check health, tail logs, tear down). This design adds a small set of self-contained Bash utilities under `scripts/` that wrap those commands into safe, predictable workflows.

## 2. Scope

### In scope

- Start the full local stack, wait for readiness, apply Phase 2 migrations, optionally seed the test repo.
- Stop the stack safely with confirmation.
- Restart the stack cleanly.
- Show service/container status and basic health.
- Tail aggregated or per-service logs.
- Reset the environment (remove volumes and recreate).
- Apply Phase 2 migrations independently.
- A reusable wait-for-health helper.
- A `scripts/utilities.md` user guide.
- Makefile shortcuts for all utilities.

### Out of scope

- Production deployment helpers (Kubernetes/Terraform already have their own workflows).
- Service-level build/test wrappers (`make test`, `make proto` remain unchanged).
- Backups/restores of Postgres/Qdrant data.
- Remote host support beyond `localhost` defaults (configurable via environment variables for future extension).

## 3. Design

### 3.1 Script inventory

All scripts live in `scripts/` and are invoked from the repository root.

| Script | Responsibility |
|---|---|
| `start_all.sh` | Build images, start `docker-compose` services, wait for Postgres + Kafka + gateway readiness, apply Phase 2 migrations, optionally seed `test-repo`. |
| `stop_all.sh` | Stop and remove the stack. Prompts for confirmation by default; `-y`/`--force` skips the prompt. |
| `restart_all.sh` | Run `stop_all.sh` then `start_all.sh` sequentially. |
| `status_all.sh` | Print `docker-compose ps` and hit the gateway `/health` endpoint (and individual service health where ports are exposed). |
| `reset_all.sh` | Stop, remove volumes, optionally prune dangling images, then run `start_all.sh` to recreate a fresh environment. Confirmation required unless `-y`. |
| `logs_all.sh` | Tail logs. Flags: `-s <service>` for per-service logs, `-n <lines>` for line count, `-f` to follow (default). |
| `apply-migrations.sh` | Apply `migrations/phase2.sql` inside the `postgres` container. |
| `wait-for-healthy.sh` | Poll `http://localhost:8000/health` until it returns HTTP 200 or a timeout is reached. |

### 3.2 Common conventions

- **POSIX safety:** All scripts start with `#!/usr/bin/env bash` and `set -euo pipefail`.
- **Repository root independence:** Scripts compute the repo root with `cd "$(dirname "$0")/.."` so they work regardless of the caller’s working directory.
- **Tooling requirements:** `docker`, `docker-compose`, `curl`, `psql` (for `apply-migrations.sh` only if run outside the container).
- **Environment variables:**
  - `COMPOSE_FILE` — path to the compose file (default: `docker-compose.yml`).
  - `REPO_INTEL_GATEWAY` — gateway health URL (default: `http://localhost:8000`).
  - `REPO_INTEL_START_TIMEOUT` — max seconds to wait for gateway health (default: `120`).
- **Exit codes:**
  - `0` — success
  - `1` — general failure (compose error, health check timeout)
  - `2` — cancelled by user
- **Destructive confirmation:** `stop_all.sh` and `reset_all.sh` prompt the user unless `-y`/`--force` is passed.

### 3.3 Makefile integration

New Makefile targets delegate to the scripts so users can use either interface:

```makefile
.PHONY: start stop restart status reset logs migrate wait

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

logs:
	bash scripts/logs_all.sh

migrate:
	bash scripts/apply-migrations.sh

wait:
	bash scripts/wait-for-healthy.sh
```

Existing targets (`build`, `up`, `down`, `logs`, `test`, `seed`, `clean`, `proto`) remain backward-compatible.

### 3.4 Documentation

A new `scripts/utilities.md` file will provide:

- A quick-start example.
- A table of scripts, flags, and exit codes.
- Environment variable reference.
- Troubleshooting (Docker not running, port conflicts, timeout tuning).
- A note that these scripts are for local development only.

## 4. Error Handling

- If Docker is not running, scripts fail fast with a clear message.
- If the gateway health check times out, the script prints the last HTTP status and exits `1`.
- `reset_all.sh` warns that all Postgres, Qdrant, and repo-storage volumes will be deleted.

## 5. Testing

- Manual smoke tests on Linux with Docker Compose.
- Verify each script from both the repo root and a subdirectory.
- Verify `-y` bypasses confirmation.
- Verify `make start`, `make stop`, `make status`, etc. work.

## 6. Future Extensions (not in this spec)

- Add `--no-build` and `--no-seed` flags to `start_all.sh` for faster iteration.
- Add `exec.sh` to run one-off commands inside a service container.
- Add support for `docker compose` (v2) plugin detection alongside legacy `docker-compose`.
