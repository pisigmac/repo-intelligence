# Repo Intelligence Platform — Future Features & TODOs

This document outlines high-impact features and architectural improvements to be implemented next in the Repo Intelligence Platform.

## 1. True Semantic Search (Real Vector Embeddings)
- **Context:** Currently, the `analysis`, `query`, and `knowledge` services use a deterministic hash-based mock (`np.random.seed(hash(text))`) for vector embeddings.
- **Action:** Replace the mock embedding logic with a real embedding model.
- **Implementation:** 
  - Integrate a local embedding model via `sentence-transformers` (e.g., `all-MiniLM-L6-v2`) or use an external API like OpenAI's `text-embedding-3-small`.
  - Update the Qdrant ingestion and search pipelines to use real multi-dimensional vectors.
- **Impact:** Enables accurate natural language queries and robust cross-repo playbook retrieval based on semantic similarity.

## 2. Robust AST Parsing via `tree-sitter`
- **Context:** The `parser` service relies on regex patterns. While improved in Phase 2, regex is inherently fragile for complex, nested syntax (e.g., heavily nested callbacks, complex decorators).
- **Action:** Replace the regex-based AST extraction with `tree-sitter`.
- **Implementation:**
  - Introduce `tree-sitter-python`, `tree-sitter-javascript`, and `tree-sitter-typescript` bindings.
  - Traverse the concrete syntax tree to extract dependencies, functions, classes, and exported entities with 100% accuracy.
- **Impact:** Eliminates edge-case parsing bugs and dramatically improves the quality of the dependency graph and extracted capabilities.

## 3. Webhook Integration (Continuous Intelligence)
- **Context:** Repositories must currently be ingested manually via the API or Web UI.
- **Action:** Add webhook receivers to the `ingestion-service`.
- **Implementation:**
  - Create endpoints to accept GitHub/GitLab webhook payloads (`push`, `pull_request`).
  - Automatically trigger the ingestion pipeline for new commits.
  - (Optional) Have the agent orchestrator automatically review code changes or optimize playbooks in the background based on PR diffs.
- **Impact:** Transforms the platform from a manual tool into a continuous, autonomous intelligence agent.

## 4. Secure Execution Environments (Sandboxing)
- **Context:** The `execution-service` modifies code and runs tests, currently executing within its own environment context.
- **Action:** Upgrade the executor to use ephemeral, isolated environments.
- **Implementation:**
  - Use Docker-in-Docker (dind) or a lightweight microVM technology (like Firecracker) to spin up isolated execution sandboxes for each playbook step.
  - Implement strict resource limits and network constraints for the sandboxed environments.
- **Impact:** Safely allows the platform to run arbitrary build scripts, tests, and code generation tasks across multiple languages without compromising the host service.


