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

# Check service health (colour table + container status)
make health

# Tail logs
make logs

# Run tests
make test          # unit + integration (if stack running)
make test-unit     # unit tests only
make test-parser   # parser-service tests only

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
| `restart_all.sh` | Stop then start the stack. Routes `-y` to stop and `--seed`/`--no-build` to start. | `bash scripts/restart_all.sh -y --seed` |
| `status_all.sh` | Show container status and gateway health. | `bash scripts/status_all.sh` |
| `logs_all.sh` | Tail aggregated or per-service logs. | `bash scripts/logs_all.sh -s execution-service -n 50` |
| `apply-migrations.sh` | Apply `migrations/phase2.sql`. | `bash scripts/apply-migrations.sh` |
| `reset_all.sh` | Stop, remove volumes, and recreate a fresh environment. | `bash scripts/reset_all.sh -y` |
| `wait-for-healthy.sh` | Block until the gateway health endpoint returns 200. | `bash scripts/wait-for-healthy.sh` |
| `health.sh` | Probe all service health endpoints and display a colour-coded table. | `bash scripts/health.sh` |
| `test.sh` | Run unit tests and (optionally) integration tests. | `bash scripts/test.sh --unit-only` |

### `test.sh` options

| Flag | Description |
|---|---|
| _(none)_ | Run all unit tests; also run integration tests if the stack is running. |
| `--unit-only` | Run unit tests only; skip integration tests even if the stack is running. |
| `--parser-only` | Run only the `services/parser/tests/` suite (fast, no Docker required). |
| `--utilities-only` | Run only `scripts/tests/test_utilities.py` (bash + compose validation). |

### `health.sh` options

| Flag | Description |
|---|---|
| _(none)_ | Print a human-readable colour table, then show container status. |
| `--json` | Emit a machine-readable JSON object instead of the table. |
| `--quiet` | Suppress all output; exit 0 if all healthy, 1 if any unhealthy. |

## Makefile targets

| Target | Equivalent command |
|---|---|
| `make start` | `bash scripts/start_all.sh` |
| `make stop` | `bash scripts/stop_all.sh` |
| `make restart` | `bash scripts/restart_all.sh` |
| `make status` | `bash scripts/status_all.sh` |
| `make health` | `bash scripts/health.sh` |
| `make migrate` | `bash scripts/apply-migrations.sh` |
| `make wait` | `bash scripts/wait-for-healthy.sh` |
| `make reset` | `bash scripts/reset_all.sh` |
| `make logs` | `docker-compose logs -f` |
| `make test` | `bash scripts/test.sh` (unit + integration) |
| `make test-unit` | `bash scripts/test.sh --unit-only` |
| `make test-parser` | `bash scripts/test.sh --parser-only` |
| `make seed` | `bash scripts/seed-data.sh` |
| `make build` | `docker-compose build` |
| `make up` | `docker-compose up -d` |
| `make down` | `docker-compose down -v` |
| `make clean` | `docker-compose down -v && docker system prune -f` |
| `make proto` | Regenerate gRPC stubs from `api/grpc/*.proto` |

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `REPO_INTEL_GATEWAY` | `http://localhost:8000` | URL of the API gateway health endpoint. |
| `REPO_INTEL_START_TIMEOUT` | `120` | Seconds to wait for the gateway to become healthy. |
| `REPO_INTEL_HEALTH_INTERVAL` | `2` | Seconds between health polls (used by `wait-for-healthy.sh`). |
| `REPO_INTEL_HEALTH_TIMEOUT` | `5` | Per-endpoint curl timeout in seconds (used by `health.sh`). |
| `COMPOSE_FILE` | `docker-compose.yml` | Standard Docker Compose variable (handled by `docker-compose`). |

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | General failure (Docker/Compose error, health timeout, unknown option, test failure) |
| `2` | Cancelled by user or no input received |

## Troubleshooting

- **Docker not running:** Scripts fail fast with an error from `docker-compose`. Start Docker first.
- **Gateway timeout:** Increase `REPO_INTEL_START_TIMEOUT`. Check service logs with `make logs`.
- **Port conflicts:** Ensure ports `8000`, `8080`, `8081`, `5434` (Postgres host port), `6333`, `8090`, `9092`, and `19092` are free.
- **Migrations fail:** Verify the `postgres` container is healthy: `make status` or `docker-compose ps`.
- **One service unhealthy in `make health`:** Run `make logs` or `docker-compose logs <service-name>` for details.
- **Parser tests fail without stack:** `make test-parser` runs entirely offline — no Docker needed.
