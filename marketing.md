# Repo Intelligence

**Turn any Git repository into a catalog of capabilities and executable playbooks.**

Repo Intelligence is an open-source, API-first platform that reads a codebase, understands what it can do, and generates runnable workflows for changing it. No more archaeology. No more stale docs. Point it at a repo and get answers.

---

## The Problem

Every codebase ships with hidden knowledge.

- What does this service actually expose?
- Where is authentication handled?
- How do I add a new protected route without breaking the existing tests?
- What changed since the last person touched this module?

Developers spend hours reading files, tracing imports, and reverse-engineering conventions before they can make a safe change. Documentation drifts. Tribal knowledge walks out the door. Onboarding is painful.

Repo Intelligence automates that discovery.

---

## The Solution

Repo Intelligence ingests a Git repository and compiles it into two concrete artifacts:

| Artifact | What it is | Example |
|----------|-----------|---------|
| **Capabilities** | Semantic descriptions of what the repo can do | `HTTP API Surface`, `JWT Authentication`, `Token Verification Middleware` |
| **Playbooks** | Executable, step-by-step workflows for changing the repo | `Add New Authenticated Endpoint`, `Debug Authentication Flow` |

Capabilities answer **"what is this?"** Playbooks answer **"how do I change it?"**

The platform is split into two phases:

- **Phase 1 — Deterministic pipeline:** ingest → parse → analyze → compile → execute.
- **Phase 2 — Self-improving loop:** execution feedback, human approvals, and cross-repo knowledge transfer so playbooks get better every time they run.

---

## Why Developers Care

- **API-first.** Everything is exposed through a clean REST gateway. Integrate it into CI, IDEs, or internal tools.
- **No model lock-in.** Phase 1 uses deterministic analysis; Phase 2 can plug in OpenAI or stay rule-based.
- **Run changes, not just read them.** Playbooks include code modifications, middleware wiring, syntax checks, tests, and git commits.
- **Learn from feedback.** Execution results are scored, low-performing playbooks are improved, and humans approve the changes before they are promoted.
- **Cross-repo knowledge.** A playbook approved in one repo can be transferred to another similar codebase.

---

## How It Works

```
Git Repository
      ↓
  Ingest (clone + commit tracking)
      ↓
  Parse (language detection, AST summaries, dependency graph)
      ↓
  Analyze (API extraction + vector embeddings)
      ↓
  Compile
      ↓
  Capabilities  ──►  Playbooks  ──►  Execution  ──►  Feedback  ──►  Improvement
```

The pipeline is event-driven with Kafka, stores state in PostgreSQL, and uses Qdrant for semantic search.

---

## 5-Minute Demo

Start the stack:

```bash
docker-compose up -d
./scripts/wait-for-healthy.sh
```

Ingest a repo:

```bash
curl -X POST http://localhost:8000/repos \
  -H 'Content-Type: application/json' \
  -d '{
    "git_url": "https://github.com/heroku/node-js-getting-started.git",
    "branch": "main"
  }'
```

Wait ~30 seconds for the pipeline to finish, then explore what was discovered:

```bash
# What can this repo do?
curl http://localhost:8000/capabilities

# What playbooks were generated?
curl http://localhost:8000/playbooks

# Ask a natural-language question
curl -X POST http://localhost:8000/query \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "how do I add a protected route",
    "top_k": 3
  }'
```

Run a playbook:

```bash
curl -X POST http://localhost:8000/execute \
  -H 'Content-Type: application/json' \
  -d '{
    "playbook_id": "<PB_ID>",
    "context": {"new_route": "/api/items", "method": "get"}
  }'
```

---

## Get Started

- **Quick start:** see [`README.md`](README.md)
- **API contract:** see [`api/openapi.yaml`](api/openapi.yaml)
- **Run locally:** `docker-compose up -d`
- **Contribute:** check the service layout in `services/` and shared libraries in `libs/`

Repo Intelligence is backend-first and ready to plug into the tools you already use. Give it a repo and see what it finds.
