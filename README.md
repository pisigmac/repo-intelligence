# Repo Intelligence Platform

A production-grade, self-evolving distributed intelligence system that ingests Git repositories, compiles them into **Capabilities (WHAT)** and **Playbooks (HOW)**, and enables AI agents to autonomously reason, execute, and improve over codebases.

## Architecture

### Phase 1: Core Pipeline
```
Git Repo → Ingestion → Parser → Analysis → Capability → Playbook → Query → Execution
                ↓           ↓           ↓              ↓
             Kafka     Kafka      Kafka         Kafka
```

### Phase 2: Autonomous Intelligence Layer
```
Execution ──► Feedback ──► Optimization ──► Approval ──► Deploy
                ↓              ↓
         Knowledge ←──── Cross-Repo Transfer
                ↓
         Agent Orchestrator (Planner → Executor → Debug → Reviewer)
```

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Make (optional)
- OpenAI API Key (optional, for LLM optimization — falls back to rule-based)

### Run Locally

```bash
cd repo-intelligence

# Build and start all services (Phase 1 + Phase 2)
docker-compose up -d

# Wait for Kafka topics (~20s)
sleep 20

# Apply Phase 2 database migrations
docker-compose exec postgres psql -U repo -d repo_intelligence -f /docker-entrypoint-initdb.d/phase2.sql
# Or manually:
# psql postgresql://repo:repo@localhost:5432/repo_intelligence -f migrations/phase2.sql

# Seed with test repository
make seed
# OR: bash scripts/seed-data.sh
```

## Web Dashboard

A React dashboard is available in `ui/`.

```bash
# Development
cd ui
npm install
npm run dev        # http://localhost:5173

# Production build + nginx
cd ui
npm run build
cd ..
docker-compose up -d
```

The dashboard is served at `http://localhost:8082` and proxies API calls to the gateway at `http://localhost:8000`.

### Test the System

```bash
# Health check
curl http://localhost:8000/health

# Phase 1: Query capabilities
curl "http://localhost:8000/capabilities"

# Phase 1: Natural language query
curl -X POST http://localhost:8000/query   -H "Content-Type: application/json"   -d '{"query": "How do I add a new protected route?"}'

# Phase 1: Execute a playbook
curl -X POST http://localhost:8000/execute   -H "Content-Type: application/json"   -d '{"playbook_id": "pb_add_auth_xxxx", "context": {"new_route": "/api/items", "method": "get"}}'

# Phase 2: Multi-agent execution
curl -X POST http://localhost:8000/agents/execute   -H "Content-Type: application/json"   -d '{"query": "Fix the auth middleware bug", "auto_approve": false}'

# Phase 2: Check playbook metrics (after some executions)
curl http://localhost:8000/feedback/pb_add_auth_001/metrics

# Phase 2: List pending approvals
curl http://localhost:8000/approvals?status=pending

# Phase 2: Approve an improvement
curl -X POST http://localhost:8000/approvals/{approval_id}/decision   -H "Content-Type: application/json"   -d '{"decision": "approved", "reviewer_notes": "Looks good"}'

# Phase 2: Search global knowledge
curl -X POST http://localhost:8000/knowledge/search   -H "Content-Type: application/json"   -d '{"query": "authentication", "language": "javascript", "framework": "express"}'

# Phase 2: Transfer playbook across repos
curl -X POST http://localhost:8000/playbooks/pb_add_auth_001/transfer   -H "Content-Type: application/json"   -d '{"target_repo_url": "https://github.com/example/target-repo.git"}'

# Run integration tests
bash scripts/integration-test.sh
bash scripts/phase2-integration-test.sh
```

## Services

### Phase 1 Services
| Service | Port | Description |
|---------|------|-------------|
| API Gateway | 8000 | REST API routing |
| Ingestion | 8080 | Clone repos, emit events |
| Parser | 8080 | AST extraction, file classification |
| Analysis | 8080 | Semantic analysis, embeddings |
| Capability | 8080 | Extract capabilities |
| Playbook | 8080 | Generate workflows |
| Query | 8080 | Intent matching, retrieval |
| Execution | 8080 | Run playbooks, modify code |
| Update | 8080 | Incremental updates |

### Phase 2 Services
| Service | Port | Description |
|---------|------|-------------|
| Feedback | 8080 | Execution telemetry, RL metrics |
| Optimization | 8080 | Auto-improve playbooks via LLM/rules |
| Knowledge | 8080 | Global store, cross-repo transfer |
| Approval | 8080 / 8081 | Human-in-the-loop workflow |
| Agent Orchestrator | 8080 | Multi-agent collaboration |

## Infrastructure

- **PostgreSQL**: Metadata + feedback + approvals + knowledge
- **Kafka (Redpanda)**: Event streaming (10 topics)
- **Qdrant**: Vector search (2 collections)
- **MinIO**: Object storage

## Self-Improvement Loop

1. **Execute** playbook → Execution service emits `execution.completed`
2. **Collect** Feedback service aggregates logs, computes score
3. **Analyze** If score < 0.60 or patterns detected → `feedback.analyzed`
4. **Optimize** Optimization service generates improved playbook v2
5. **Queue** Approval service creates pending approval
6. **Review** Human approves/rejects via API or WebSocket
7. **Deploy** Approved playbook replaces old version in queries
8. **Learn** High-scoring playbooks promoted to global knowledge

## Multi-Agent Execution

```
User Query
  → Planner: selects capability + playbook
  → Executor: runs playbook steps
  → [FAIL] → Debug: diagnoses failure, suggests patch
  → Executor: retries with patch (up to 2 times)
  → Reviewer: validates output, checks security
  → [PASS] → Complete
```

## Development

### Project Structure
```
repo-intelligence/
├── docker-compose.yml
├── Makefile
├── migrations/
│   └── phase2.sql
├── api/                  # OpenAPI + gRPC specs
├── libs/                 # Shared libraries
│   ├── common/           # Config, DB, Kafka, logging
│   ├── models/           # Pydantic domain models + ORM
│   ├── utils/            # Git helpers
│   └── agents/           # Agent base classes
├── services/             # Microservices
│   ├── ingestion/
│   ├── parser/
│   ├── analysis/
│   ├── capability/
│   ├── playbook/
│   ├── query/
│   ├── execution/
│   ├── update/
│   ├── feedback/         # Phase 2
│   ├── optimization/     # Phase 2
│   ├── knowledge/        # Phase 2
│   ├── approval/         # Phase 2
│   └── agent-orchestrator/  # Phase 2
│       └── agents/
│           ├── planner.py
│           ├── executor.py
│           ├── debug.py
│           └── reviewer.py
├── infra/                # Docker, K8s, Terraform
├── scripts/              # Seed & test scripts
└── test-repo/            # Sample Express app
```

### Database Migrations

Phase 1 schema is auto-created by `scripts/init-db.sql`.
Phase 2 schema requires running `migrations/phase2.sql`:

```bash
psql postgresql://repo:repo@localhost:5432/repo_intelligence -f migrations/phase2.sql
```

### Running Tests

```bash
# Unit tests
make test

# Phase 1 integration
bash scripts/integration-test.sh

# Phase 2 integration (feedback, optimization, approval)
bash scripts/phase2-integration-test.sh
```

## Production Deployment

### Kubernetes
```bash
kubectl apply -f infra/k8s/
```

### Terraform (AWS)
```bash
cd infra/terraform
terraform init
terraform apply
```

## Design Principles

- **Clean Architecture**: Domain logic independent of frameworks
- **Event-Driven**: Async pipeline for heavy processing
- **Idempotency**: Safe to retry ingestion and execution
- **Observability**: Structured JSON logging, health checks, execution telemetry
- **Extensibility**: Pluggable parsers, step types, LLM backends
- **Self-Improvement**: Feedback loop with human oversight
- **Agent Collaboration**: Specialized agents with accountability

## License
MIT
