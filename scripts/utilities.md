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
| `restart_all.sh` | Stop then start the stack. Routes `-y` to stop and `--seed`/`--no-build` to start. | `bash scripts/restart_all.sh -y --seed` |
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
| `2` | Cancelled by user or no input received |

## Troubleshooting

- **Docker not running:** Scripts fail fast with an error from `docker-compose`. Start Docker first.
- **Gateway timeout:** Increase `REPO_INTEL_START_TIMEOUT`. Check service logs with `make logs`.
- **Port conflicts:** Ensure ports `8000`, `8080`, `8081`, `5434` (Postgres host port), `6333`, `9092`, and `19092` are free.
- **Migrations fail:** Verify the `postgres` container is healthy: `make status` or `docker-compose ps`.
