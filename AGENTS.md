# Repo Intelligence Platform — Agent Guide

This document is written for AI coding agents. It describes the project structure, technology stack, build/test workflows, and conventions you need to know before modifying code.

## Project Overview

Repo Intelligence Platform is a production-oriented, self-evolving distributed intelligence system. It ingests Git repositories, compiles them into **Capabilities** (WHAT the codebase can do) and **Playbooks** (HOW to perform changes), and lets AI agents autonomously reason about, execute, and improve codebases.

The system is split into two phases:

- **Phase 1 — Core Pipeline**: `Git Repo → Ingestion → Parser → Analysis → Capability → Playbook → Query → Execution`.
- **Phase 2 — Autonomous Intelligence Layer**: execution feedback is aggregated, playbooks are auto-improved, improvements go through human approval, and an agent orchestrator can plan, execute, debug, and review tasks.

The public entry point is an API Gateway on `http://localhost:8000`. Individual microservices listen on port `8080` inside the Docker network.

## Technology Stack

- **Language**: Python 3.11.
- **Web framework**: FastAPI + Uvicorn.
- **Data validation / settings**: Pydantic v2 + `pydantic-settings`.
- **Database access**: SQLAlchemy 2.0 with asyncpg (async PostgreSQL driver).
- **Database**: PostgreSQL 15.
- **Event streaming**: Redpanda (Kafka-compatible) via `aiokafka`.
- **Vector search**: Qdrant.
- **Object storage**: MinIO is mentioned in documentation but not wired into `docker-compose.yml`.
- **Container runtime**: Docker and Docker Compose.
- **Container orchestration**: Kubernetes manifests under `infra/k8s/`.
- **Cloud provisioning**: Terraform for AWS ECS/RDS/S3 under `infra/terraform/`.
- **Optional LLM**: OpenAI-compatible API for playbook optimization; falls back to rule-based mock when no key is provided.

There is **no root `pyproject.toml`, `package.json`, or `Cargo.toml`**. Each Python service carries its own `requirements.txt` and is built with its own Dockerfile.

## Project Structure

```
repo-intelligence/
├── docker-compose.yml           # Full local stack (Phase 1 + Phase 2)
├── Makefile                     # Common commands
├── pytest.ini                   # Pytest configuration
├── conftest.py                  # Shared pytest fixtures
├── README.md                    # Human-facing quick start
├── AGENTS.md                    # This file
│
├── api/
│   ├── openapi.yaml             # REST API OpenAPI spec
│   └── grpc/                    # Protobuf service definitions
│
├── libs/                        # Shared Python libraries
│   ├── common/                  # Config, DB, Kafka, logging
│   ├── models/                  # Pydantic domain models + SQLAlchemy ORM
│   ├── utils/                   # Git helpers
│   └── agents/                  # Base agent classes and Kafka message bus
│
├── services/                    # Microservices (each has main.py + requirements.txt)
│   ├── ingestion/               # Clone repos, emit repo.ingested events
│   ├── parser/                  # Language detection, regex-based AST summary
│   ├── analysis/                # Embeddings, API extraction
│   ├── capability/              # Extract capabilities into PostgreSQL
│   ├── playbook/                # Generate playbooks from capabilities
│   ├── query/                   # Intent matching + retrieval
│   ├── execution/               # Run playbook steps, modify code, run tests
│   ├── update/                  # Listen to execution.completed, incremental updates
│   ├── feedback/                # Aggregate execution telemetry, compute RL metrics
│   ├── optimization/            # Improve playbooks via LLM/rules
│   ├── knowledge/               # Global knowledge store, cross-repo transfer
│   ├── approval/                # Human-in-the-loop approval workflow
│   └── agent-orchestrator/      # Planner / Executor / Debug / Reviewer agents
│
├── infra/
│   ├── docker/                  # Gateway Dockerfile + shared service Dockerfile
│   ├── k8s/                     # Kubernetes manifests
│   └── terraform/               # AWS Terraform modules
│
├── migrations/
│   └── phase2.sql               # Phase 2 schema additions
│
├── scripts/
│   ├── init-db.sql              # Phase 1 schema (auto-run by postgres container)
│   ├── seed-data.sh             # Seed with test-repo
│   ├── integration-test.sh      # Phase 1 end-to-end smoke test
│   └── phase2-integration-test.sh
│
└── test-repo/                   # Sample Express app used for local testing
```

## Build and Run Commands

### Local development (Docker Compose)

```bash
# Build and start everything
docker-compose up -d

# Wait for Kafka topics to be created, then apply Phase 2 migrations
sleep 20
docker-compose exec postgres psql -U repo -d repo_intelligence -f /docker-entrypoint-initdb.d/phase2.sql
# Or from host:
# psql postgresql://repo:repo@localhost:5432/repo_intelligence -f migrations/phase2.sql

# Seed with the sample repository
make seed
```

### Makefile targets

| Target | Command |
|--------|---------|
| Build images | `make build` |
| Start stack | `make up` |
| Stop stack and remove volumes | `make down` |
| Tail logs | `make logs` |
| Run unit tests | `make test` |
| Seed test repo | `make seed` |
| Clean Docker resources | `make clean` |
| Regenerate gRPC code | `make proto` |

### gRPC code generation

```bash
make proto
# Equivalent to:
python -m grpc_tools.protoc -Iapi/grpc --python_out=libs/models --grpc_python_out=libs/models api/grpc/*.proto
```

## Configuration and Environment

Configuration is centralized in `libs/common/config.py` using `pydantic-settings`. Key environment variables:

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `postgresql+asyncpg://repo:repo@localhost/repo_intelligence` | PostgreSQL connection |
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Kafka/Redpanda brokers |
| `KAFKA_GROUP_ID` | `repo-intel` | Consumer group prefix |
| `QDRANT_URL` | `http://localhost:6333` | Vector database |
| `REPO_STORAGE_PATH` | `/tmp/repos` | Local repo clone path |
| `LOG_LEVEL` | `INFO` | Logging level |
| `OPENAI_API_KEY` | empty | Optional; enables LLM optimization |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | OpenAI-compatible endpoint |
| `OPENAI_MODEL` | `gpt-4` | Model for optimization |

Service URLs used by the gateway and orchestrator are hard-coded to Docker Compose service names by default (e.g. `http://query-service:8080`).

## Service Architecture

### Phase 1 pipeline

1. **ingestion-service** clones a repo, records it in `repos`, emits `repo.ingested`.
2. **parser-service** consumes `repo.ingested`, parses files with regex-based AST summaries, emits `repo.parsed`.
3. **analysis-service** consumes `repo.parsed`, builds semantic chunks, stores Qdrant embeddings, emits `repo.analyzed`.
4. **capability-service** consumes `repo.analyzed`, extracts capabilities into `capabilities`, emits `capability.generated`.
5. **playbook-service** consumes `capability.generated`, generates playbooks into `playbooks`, emits `playbook.generated`.
6. **query-service** answers natural-language queries by keyword + vector search.
7. **execution-service** runs playbook steps against a repo (code modification, tests, git commit, rollback).
8. **update-service** listens to `execution.completed` for cache invalidation / notifications.

### Phase 2 autonomous layer

1. **feedback-service** consumes `execution.completed`, writes `feedback`, computes success rate / score, emits `feedback.analyzed` when score < 0.60 or failure patterns are detected.
2. **optimization-service** consumes `feedback.analyzed`, generates an improved playbook draft via `LLMClient` (OpenAI or rule-based mock), creates an `approvals` record, emits `playbook.improved`.
3. **approval-service** exposes WebSocket `/ws/approvals` and REST endpoints; on approval updates the playbook `status` to `approved` and emits `playbook.approved`.
4. **knowledge-service** indexes approved playbooks into `global_knowledge` and Qdrant, supports semantic search and cross-repo playbook transfer.
5. **agent-orchestrator** coordinates Planner → Executor → Debug (up to 2 retries) → Reviewer agents and submits final feedback.

### Kafka topics

Created by `init-kafka` in `docker-compose.yml`:

- `repo.ingested`
- `repo.parsed`
- `repo.analyzed`
- `capability.generated`
- `playbook.generated`
- `execution.requested`
- `execution.completed`
- `feedback.analyzed`
- `playbook.improved`
- `playbook.approved`
- `playbook.transferred`
- `agent.task`
- `agent.response`

Events use a CloudEvents-like envelope (`specversion`, `type`, `source`, `id`, `time`, `datacontenttype`, `data`).

## Code Organization Conventions

- **Shared code lives in `libs/`**. Services import it with `sys.path.insert(0, "/app")` and `from libs.common import ...`.
- **Each service is a Python package** mounted at `/app/service/` inside its container, with `main.py` as the entry point. Run via `python -m service.main`.
- **Domain models**: Pydantic models in `libs/models/domain.py`; SQLAlchemy ORM models in `libs/models/orm.py`.
- **Database sessions**: `libs/common/db.py` provides `AsyncSessionLocal`, `get_db()` FastAPI dependency, and `engine`. The pattern in services is often to open `AsyncSessionLocal()` directly in background tasks because dependencies do not propagate to `BackgroundTasks`.
- **Logging**: `libs/common/logging_config.py` emits structured JSON logs via `python-json-logger`. Always call `configure_logging(settings.app_name, settings.log_level)` at service startup.
- **Health checks**: Every service exposes `GET /health` returning `{"status": "ok", "service": "<name>"}`.
- **Lifespan management**: Kafka producers/consumers are started in FastAPI `lifespan` context managers and cancelled/stopped on shutdown.

## Testing

### Unit tests

```bash
make test
# Equivalent to:
pytest services/*/tests/ -v
```

`pytest.ini` enables `asyncio_mode = auto` and scans `services/*/tests`. As of this writing only `services/ingestion/tests/test_main.py` and `services/parser/tests/test_main.py` contain tests. Several `tests/` directories exist but are empty.

### Integration tests

Run these against a fully started local stack:

```bash
# Phase 1
bash scripts/integration-test.sh

# Phase 2
bash scripts/phase2-integration-test.sh
```

These scripts ingest `test-repo`, wait for the pipeline, query capabilities/playbooks, execute a playbook, check feedback metrics, run the agent orchestrator, list approvals, and search knowledge.

### Manual smoke checks

```bash
curl http://localhost:8000/health
curl -X POST http://localhost:8000/repos -H "Content-Type: application/json" \
  -d '{"git_url": "file:///app/test-repo", "branch": "main"}'
curl "http://localhost:8000/capabilities"
curl -X POST http://localhost:8000/query -H "Content-Type: application/json" \
  -d '{"query": "How do I add a new protected route?"}'
```

## Code Style Guidelines

- Follow existing service style: top-level module docstring, imports, `sys.path.insert(0, "/app")`, then `settings = get_settings()` and `logger = configure_logging(...)`.
- Use Pydantic v2 syntax (`model_dump`, `ConfigDict(from_attributes=True)`).
- Prefer `async`/`await` for DB and HTTP calls.
- Construct raw SQL with `sqlalchemy.text` and use parameter binding; avoid f-strings for SQL.
- Keep Kafka event payloads JSON-serializable dicts.
- Use `uuid.uuid4().hex[:8]` for short identifiers in generated playbooks/capabilities.
- When adding a new service, create `services/<name>/main.py`, `services/<name>/requirements.txt`, and either reuse `infra/docker/Dockerfile.service` with `args.SERVICE` or add a dedicated `Dockerfile`.

## Security Considerations

- Do **not** commit `.env` files or database credentials.
- The reviewer agent flags potential secret exposure in execution logs (looks for `password`, `secret`, `token` without masking).
- Sensitive file modifications (`.env`, files containing `secret`) are flagged by the reviewer agent.
- Git authentication tokens are accepted in ingestion requests but must be handled securely; the service injects them into HTTPS clone URLs in memory only.
- Kubernetes secrets are defined in `infra/k8s/secret.yaml` with a placeholder password; replace with a generated secret before production use.
- Terraform generates a random database password but stores state securely is the operator's responsibility.

## Important Implementation Notes

- **Embeddings are deterministic mocks**: `analysis-service`, `query-service`, and `knowledge-service` use a hash-based random vector (`np.random.seed(hash(text))`) for MVP. Replace with a real embedding model for production semantic search.
- **Parser uses regex, not a full parser**: JavaScript/TypeScript/Python parsing is regex-based. It works for the sample Express app but will miss complex constructs.
- **Optimization has a rule-based fallback**: If `OPENAI_API_KEY` is unset, `LLMClient` uses `_mock_optimize` to add dependency checks, syntax validation, checkpoints, and preconditions based on failure patterns.
- **Approval is required before deployment**: Improved playbooks are inserted with `status = 'draft'` and an `approvals` row. The query service currently does not filter on `status` in all paths; check behavior when adding approval-aware retrieval.
- **Cross-repo transfer** clones the target repository briefly to detect language/framework and adapts step targets heuristically.

## Deployment

### Docker Compose (local)

See "Build and Run Commands" above.

### Kubernetes

```bash
kubectl apply -f infra/k8s/
```

Manifests include namespace, configmap, secret, deployment/service for `query-service`, and an HPA. Other services follow the same pattern.

### Terraform (AWS)

```bash
cd infra/terraform
terraform init
terraform apply
```

This provisions an ECS cluster, RDS PostgreSQL instance, ECR repository, S3 bucket, and CloudWatch log group. It is a starting template and not a complete production environment.
