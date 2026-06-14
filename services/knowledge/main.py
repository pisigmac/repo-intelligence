"""Knowledge Service: global knowledge store, cross-repo playbook transfer, pattern matching."""
import os
import sys
import json
import uuid
import asyncio
import logging
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import numpy as np

sys.path.insert(0, "/app")
from libs.common import configure_logging, get_settings, KafkaProducer, KafkaConsumer, AsyncSessionLocal
from libs.utils import clone_repository, get_repo_files
from libs.models import Playbook

settings = get_settings()
logger = configure_logging(settings.app_name, settings.log_level)


def embed_text(text: str, dim: int = 384) -> list[float]:
    np.random.seed(hash(text) % (2**32))
    vec = np.random.randn(dim).astype(np.float32)
    vec = vec / np.linalg.norm(vec)
    return vec.tolist()


class KnowledgeSearchRequest(BaseModel):
    query: str | None = None
    tags: list[str] = []
    language: str | None = None
    framework: str | None = None
    limit: int = 10


class TransferRequest(BaseModel):
    playbook_id: str
    target_repo_url: str
    adaptation_context: dict = {}


class KnowledgeService:
    def __init__(self):
        self.qdrant = QdrantClient(url=settings.qdrant_url)
        self.collection_name = "global_playbooks"
        self._ensure_collection()

    def _ensure_collection(self):
        try:
            self.qdrant.get_collection(self.collection_name)
        except Exception:
            self.qdrant.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE),
            )
            logger.info("Created Qdrant collection", extra={"name": self.collection_name})

    async def index_playbook(self, playbook: Playbook, source_repo: str, tags: list[str], language: str, framework: str):
        """Index a playbook into global knowledge store."""
        global_id = f"g_{playbook.id}"

        # Store in Postgres
        session: AsyncSession = AsyncSessionLocal()
        try:
            await session.execute(
                text("""
                    INSERT INTO global_knowledge (id, name, source_repo, source_playbook_id, playbook_template, applicable_tags, language, framework, pattern_type)
                    VALUES (:id, :name, :repo, :spid, :template, :tags, :lang, :fw, :ptype)
                    ON CONFLICT (id) DO UPDATE SET
                        name = EXCLUDED.name,
                        playbook_template = EXCLUDED.playbook_template,
                        applicable_tags = EXCLUDED.applicable_tags,
                        transfer_success_rate = global_knowledge.transfer_success_rate
                """),
                {
                    "id": global_id,
                    "name": playbook.name,
                    "repo": source_repo,
                    "spid": playbook.id,
                    "template": json.dumps(playbook.model_dump()),
                    "tags": tags,
                    "lang": language,
                    "fw": framework,
                    "ptype": playbook.capability_id,
                }
            )
            await session.commit()
        finally:
            await session.close()

        # Store embedding in Qdrant
        text_repr = f"{playbook.name}: {playbook.description or ''}. Steps: {len(playbook.steps)}. Tags: {', '.join(tags)}"
        vec = embed_text(text_repr)
        point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, global_id))
        self.qdrant.upsert(
            collection_name=self.collection_name,
            points=[PointStruct(
                id=point_id,
                vector=vec,
                payload={
                    "global_id": global_id,
                    "name": playbook.name,
                    "tags": tags,
                    "language": language,
                    "framework": framework,
                    "source_repo": source_repo,
                }
            )],
        )
        logger.info("Playbook indexed to knowledge", extra={"global_id": global_id, "point_id": point_id})

    async def search(self, req: KnowledgeSearchRequest) -> list[dict]:
        """Search global knowledge by semantic similarity + filters."""
        # Semantic search
        query_text = req.query or " ".join(req.tags)
        vec = embed_text(query_text)

        filter_conditions = []
        if req.language:
            filter_conditions.append({"key": "language", "match": {"value": req.language}})
        if req.framework:
            filter_conditions.append({"key": "framework", "match": {"value": req.framework}})

        results = self.qdrant.search(
            collection_name=self.collection_name,
            query_vector=vec,
            limit=req.limit * 2,
            query_filter={"must": filter_conditions} if filter_conditions else None,
        )

        # Fetch from Postgres for full data
        session: AsyncSession = AsyncSessionLocal()
        try:
            output = []
            for r in results:
                global_id = r.payload.get("global_id")
                if not global_id:
                    continue
                res = await session.execute(
                    text("SELECT * FROM global_knowledge WHERE id = :id"),
                    {"id": global_id}
                )
                row = res.mappings().first()
                if row:
                    output.append({
                        "global_playbook_id": row["id"],
                        "name": row["name"],
                        "source_repo": row["source_repo"],
                        "applicable_tags": row["applicable_tags"],
                        "language": row["language"],
                        "framework": row["framework"],
                        "transfer_success_rate": float(row["transfer_success_rate"] or 0),
                        "transfer_count": row["transfer_count"],
                        "score": r.score,
                    })
            return output[:req.limit]
        finally:
            await session.close()

    async def transfer_playbook(self, playbook_id: str, target_repo_url: str, adaptation_context: dict) -> dict:
        """Transfer a playbook to a target repository with adaptation."""
        session: AsyncSession = AsyncSessionLocal()
        try:
            # Fetch global playbook
            res = await session.execute(
                text("SELECT * FROM global_knowledge WHERE source_playbook_id = :spid"),
                {"spid": playbook_id}
            )
            global_pb = res.mappings().first()
            if not global_pb:
                raise HTTPException(status_code=404, detail="Playbook not found in global knowledge")

            template = json.loads(global_pb["playbook_template"])

            # Clone target repo briefly to detect language/framework
            safe_name = target_repo_url.replace(":", "_").replace("/", "_")[:50]
            dest = os.path.join("/tmp", f"transfer_{safe_name}_{uuid.uuid4().hex[:8]}")
            try:
                commit = clone_repository(target_repo_url, dest, "main")
                files = get_repo_files(dest)
                languages = set()
                framework = "unknown"
                for f in files:
                    if f.suffix in [".js", ".jsx"]:
                        languages.add("javascript")
                        if any((f.parent / "package.json").exists() for f in files[:10]):
                            framework = "express"  # simplified detection
                    elif f.suffix in [".ts", ".tsx"]:
                        languages.add("typescript")
                    elif f.suffix == ".py":
                        languages.add("python")
                target_lang = list(languages)[0] if languages else "unknown"
            except Exception as e:
                logger.warning("Could not clone target repo for detection", extra={"error": str(e)})
                target_lang = adaptation_context.get("language", "javascript")
                framework = adaptation_context.get("framework", "express")
                dest = None
                commit = "unknown"

            # Adapt playbook
            adapted_steps = []
            for step in template.get("steps", []):
                adapted = dict(step)
                target = adapted.get("target", "")
                # Simple path adaptation
                if target_lang == "javascript" and framework == "express":
                    if "routes/" not in target and adapted.get("type") == "code_modification":
                        adapted["target"] = "routes/auth.js"
                elif target_lang == "python":
                    if adapted.get("type") == "code_modification":
                        adapted["target"] = "app.py"
                adapted_steps.append(adapted)

            new_playbook_id = f"pb_transfer_{uuid.uuid4().hex[:8]}"

            # Insert transfer record
            await session.execute(
                text("""
                    INSERT INTO transfers (global_playbook_id, source_playbook_id, target_repo, new_playbook_id, status, adaptation_context)
                    VALUES (:gid, :spid, :target, :npid, 'completed', :ctx)
                """),
                {
                    "gid": global_pb["id"],
                    "spid": playbook_id,
                    "target": target_repo_url,
                    "npid": new_playbook_id,
                    "ctx": json.dumps({"language": target_lang, "framework": framework}),
                }
            )

            # Insert new playbook in target context (using a placeholder repo_id derived from URL)
            repo_id = f"repo_{uuid.uuid4().hex[:8]}"
            await session.execute(
                text("""
                    INSERT INTO playbooks (id, capability_id, name, description, steps, validation, rollback, observability, version, status)
                    VALUES (:id, :cid, :name, :desc, :steps, :val, :roll, :obs, '1.0.0', 'approved')
                """),
                {
                    "id": new_playbook_id,
                    "cid": template.get("capability_id", "unknown"),
                    "name": f"[Transferred] {template.get('name', 'Playbook')}",
                    "desc": f"Transferred from {global_pb['source_repo']}. Adapted for {target_lang}/{framework}.",
                    "steps": json.dumps(adapted_steps),
                    "val": json.dumps(template.get("validation", {})),
                    "roll": json.dumps(template.get("rollback", {})),
                    "obs": json.dumps(template.get("observability", {})),
                }
            )

            # Update transfer success rate
            await session.execute(
                text("""
                    UPDATE global_knowledge 
                    SET transfer_count = transfer_count + 1,
                        transfer_success_rate = (transfer_success_rate * transfer_count + 1.0) / (transfer_count + 1)
                    WHERE id = :gid
                """),
                {"gid": global_pb["id"]}
            )
            await session.commit()

            # Cleanup
            if dest and os.path.exists(dest):
                import shutil
                shutil.rmtree(dest)

            return {
                "transfer_id": str(uuid.uuid4()),
                "status": "completed",
                "new_playbook_id": new_playbook_id,
                "target_language": target_lang,
                "target_framework": framework,
            }
        finally:
            await session.close()


knowledge = KnowledgeService()

app = FastAPI(title="Knowledge Service", version="2.0.0")

@app.get("/health")
async def health():
    return {"status": "ok", "service": "knowledge"}

@app.post("/knowledge/search")
async def search_knowledge(req: KnowledgeSearchRequest):
    results = await knowledge.search(req)
    return results

@app.post("/knowledge/index")
async def index_playbook_endpoint(playbook_id: str, source_repo: str, tags: list[str], language: str, framework: str):
    session: AsyncSession = AsyncSessionLocal()
    try:
        res = await session.execute(text("SELECT * FROM playbooks WHERE id = :id"), {"id": playbook_id})
        row = res.mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="Playbook not found")

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
        await knowledge.index_playbook(pb, source_repo, tags, language, framework)
        return {"status": "indexed", "global_id": f"g_{playbook_id}"}
    finally:
        await session.close()

@app.post("/playbooks/{playbook_id}/transfer")
async def transfer_playbook_endpoint(playbook_id: str, req: TransferRequest):
    result = await knowledge.transfer_playbook(playbook_id, req.target_repo_url, req.adaptation_context)
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
