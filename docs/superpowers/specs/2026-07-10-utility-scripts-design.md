# Utility Scripts Design

## Overview

Add three missing local-development utility scripts to the `scripts/` directory:

- `setup.sh` — one-time environment setup
- `test.sh` — run unit and integration tests
- `health.sh` — check all service health endpoints

Existing scripts (`start_all.sh`, `stop_all.sh`, `restart_all.sh`, `status_all.sh`, `logs_all.sh`, `reset_all.sh`, `wait-for-healthy.sh`, `apply-migrations.sh`, `seed-data.sh`) are left unchanged.

## Goals

- Make first-time setup a single command.
- Make running the full test suite a single command.
- Make checking every service's health a single command.
- Keep the new scripts consistent with the current bash style in `scripts/`.

## Non-goals

- No shared helper library or refactor of existing scripts.
- No production deployment logic.
- No changes to service code.

## Scripts

### `scripts/setup.sh`

Purpose: verify the local environment is ready and build images.

Behavior:

1. Verify `docker` and `docker-compose` are installed and runnable.
2. If `.env` does not exist, create it with local-development defaults (`OPENAI_API_KEY=` and `CORS_ORIGINS=http://localhost:8090`).
3. Run `docker-compose build`.
4. Print a success message and the next steps (`make start` or `bash scripts/start_all.sh`).

Usage:

```bash
bash scripts/setup.sh
bash scripts/setup.sh --help
```

Flags:

| Flag | Description |
|---|---|
| `-h`, `--help` | Show usage and exit. |

### `scripts/test.sh`

Purpose: run the full local test suite.

Behavior:

1. Run unit tests with `pytest services/*/tests/ -v`.
2. If unit tests pass and the stack appears running, run Phase 1 integration tests via `scripts/integration-test.sh`.
3. If Phase 1 integration tests pass, run Phase 2 integration tests via `scripts/phase2-integration-test.sh`.
4. Exit with the first non-zero status encountered.

Usage:

```bash
bash scripts/test.sh
bash scripts/test.sh --unit-only
bash scripts/test.sh --help
```

Flags:

| Flag | Description |
|---|---|
| `--unit-only` | Run only pytest unit tests. |
| `-h`, `--help` | Show usage and exit. |

### `scripts/health.sh`

Purpose: probe the `/health` endpoint of every service defined in `docker-compose.yml`.

Behavior:

1. Parse service names from `docker-compose.yml`.
2. For each running service, call its internal `/health` endpoint via `docker-compose exec <service> wget -qO- http://localhost:8080/health` (services listen on port 8080 inside the container).
3. Print a table with service name, URL, status, and response time.
4. Exit non-zero if any service is unhealthy or unreachable.

Usage:

```bash
bash scripts/health.sh
bash scripts/health.sh --help
```

Flags:

| Flag | Description |
|---|---|
| `-h`, `--help` | Show usage and exit. |

## Documentation updates

- Update `scripts/utilities.md` to document the three new scripts, their usage, and exit codes.
- Update `Makefile` to add convenient targets: `setup`, `test`, `health`.

## Style conventions

Each new script follows the existing convention:

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"
```

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | General failure (missing prerequisite, test failure, unhealthy service, unknown option) |
| `2` | Cancelled by user (not expected for these scripts) |

## Testing the change

1. Run `bash scripts/setup.sh` on a clean checkout and verify it creates `.env` and builds images.
2. Run `bash scripts/test.sh --unit-only` and verify pytest executes.
3. Start the stack with `make start`, then run `bash scripts/health.sh` and verify all services report healthy.
