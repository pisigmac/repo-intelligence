# Repo Intelligence Platform — Future Features & TODOs

This document outlines high-impact features and architectural improvements to be implemented next in the Repo Intelligence Platform.

## 1. True Semantic Search (Real Vector Embeddings)
- **Context:** Currently, the `analysis`, `query`, and `knowledge` services use a deterministic hash-based mock (`np.random.seed(hash(text))`) for vector embeddings.
- **Action:** Replace the mock embedding logic with a real embedding model.
- **Implementation:** 
  - Integrate a local embedding model via `sentence-transformers` (e.g., `all-MiniLM-L6-v2`) or use an external API like OpenAI's `text-embedding-3-small`.
  - Update the Qdrant ingestion and search pipelines to use real multi-dimensional vectors.
- **Impact:** Enables accurate natural language queries and robust cross-repo playbook retrieval based on semantic similarity.
