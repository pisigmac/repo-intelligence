"""Query Service: intent detection, capability matching, playbook retrieval."""
import os
import sys
import json
import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession
from qdrant_client import QdrantClient
import numpy as np

sys.path.insert(0, "/app")
from libs.common import configure_logging, get_settings, get_db
from libs.models import Capability, Playbook, QueryResult

settings = get_settings()
logger = configure_logging(settings.app_name, settings.log_level)


from libs.common.embeddings import get_embedding


class QueryRequest(BaseModel):
    query: str
    repo: str | None = None
    top_k: int = 5


class QueryService:
    def __init__(self):
        self.qdrant = QdrantClient(url=settings.qdrant_url)
        self.collection = "repo_embeddings"

    def semantic_search(self, query: str, limit: int = 10) -> list[dict]:
        try:
            vec = get_embedding(query)
            results = self.qdrant.search(
                collection_name=self.collection,
                query_vector=vec,
                limit=limit,
            )
            return [{"id": r.id, "score": r.score, "payload": r.payload} for r in results]
        except Exception as e:
            logger.warning("Vector search failed", extra={"error": str(e)})
            return []

    async def query_capabilities(self, session: AsyncSession, query: str, repo: str | None = None, top_k: int = 5) -> tuple[list[Capability], float]:
        # Semantic search for relevant repo chunks
        semantic_results = self.semantic_search(query, limit=top_k * 3)

        # Keyword matching on capabilities
        sql = select(text("*")).select_from(text("capabilities"))
        conditions = []
        if repo:
            conditions.append(f"repo = '{repo}'")

        query_lower = query.lower()
        keyword_conditions = []
        keywords = [k for k in query_lower.split() if len(k) > 3]
        for kw in keywords:
            keyword_conditions.append(f"(name ILIKE '%{kw}%' OR description ILIKE '%{kw}%' OR category ILIKE '%{kw}%')")

        if keyword_conditions:
            conditions.append("(" + " OR ".join(keyword_conditions) + ")")

        if conditions:
            sql = sql.where(text(" AND ".join(conditions)))

        sql = sql.limit(top_k)
        result = await session.execute(sql)
        rows = result.mappings().all()

        capabilities = []
        for row in rows:
            cap = Capability(
                id=row["id"],
                name=row["name"],
                description=row["description"],
                category=row["category"],
                repo=row["repo"],
                commit=row["commit"],
                entry_points=json.loads(row["entry_points"]) if row["entry_points"] else [],
                interfaces=json.loads(row["interfaces"]) if row["interfaces"] else {},
                dependencies=row["dependencies"] or [],
                signals=json.loads(row["signals"]) if row["signals"] else {},
            )
            capabilities.append(cap)

        # Calculate confidence based on semantic scores
        confidence = 0.0
        if semantic_results:
            confidence = min(0.95, semantic_results[0]["score"] * 1.2)
        elif capabilities:
            confidence = 0.75

        return capabilities, confidence

    async def get_playbooks_for_capabilities(self, session: AsyncSession, cap_ids: list[str]) -> list[Playbook]:
        if not cap_ids:
            return []

        placeholders = ",".join([f"'{c}'" for c in cap_ids])
        result = await session.execute(
            text(f"SELECT * FROM playbooks WHERE capability_id IN ({placeholders})")
        )
        rows = result.mappings().all()
        playbooks = []
        for row in rows:
            pb = Playbook(
                id=row["id"],
                capability_id=row["capability_id"],
                name=row["name"],
                description=row["description"],
                steps=json.loads(row["steps"]) if row["steps"] else [],
                validation=json.loads(row["validation"]) if row["validation"] else {},
                rollback=json.loads(row["rollback"]) if row["rollback"] else {},
                observability=json.loads(row["observability"]) if row["observability"] else {},
            )
            playbooks.append(pb)
        return playbooks


query_service = QueryService()

app = FastAPI(title="Query Service", version="1.0.0")

@app.get("/health")
async def health():
    return {"status": "ok", "service": "query"}

@app.get("/capabilities")
async def list_capabilities(repo: str | None = None, category: str | None = None, session: AsyncSession = Depends(get_db)):
    sql = select(text("*")).select_from(text("capabilities"))
    conditions = []
    if repo:
        conditions.append(f"repo = '{repo}'")
    if category:
        conditions.append(f"category = '{category}'")
    if conditions:
        sql = sql.where(text(" AND ".join(conditions)))

    result = await session.execute(sql)
    rows = result.mappings().all()
    return [dict(r) for r in rows]

@app.get("/playbooks")
async def list_playbooks(capability_id: str | None = None, repo: str | None = None, session: AsyncSession = Depends(get_db)):
    sql = select(text("*")).select_from(text("playbooks"))
    conditions = []
    if capability_id:
        conditions.append(f"capability_id = '{capability_id}'")
    if repo:
        # Join with capabilities to filter by repo
        sql = sql.select_from(text("playbooks p JOIN capabilities c ON p.capability_id = c.id"))
        conditions.append(f"c.repo = '{repo}'")
    if conditions:
        sql = sql.where(text(" AND ".join(conditions)))

    result = await session.execute(sql)
    rows = result.mappings().all()
    return [dict(r) for r in rows]

@app.post("/query", response_model=QueryResult)
async def query_system(req: QueryRequest, session: AsyncSession = Depends(get_db)):
    logger.info("Query received", extra={"query": req.query, "repo": req.repo})

    capabilities, confidence = await query_service.query_capabilities(
        session, req.query, req.repo, req.top_k
    )

    cap_ids = [c.id for c in capabilities]
    playbooks = await query_service.get_playbooks_for_capabilities(session, cap_ids)

    return QueryResult(
        capabilities=capabilities,
        playbooks=playbooks,
        confidence=confidence,
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
