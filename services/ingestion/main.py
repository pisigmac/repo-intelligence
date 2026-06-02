"""Ingestion Service: clones repos, tracks commits, emits repo.ingested events."""
import os
import sys
import uuid
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, "/app")
from libs.common import configure_logging, get_settings, KafkaProducer, get_db, AsyncSessionLocal
from libs.models.orm import RepoORM
from libs.utils import clone_repository

settings = get_settings()
logger = configure_logging(settings.app_name, settings.log_level)

# Pydantic models for API
class IngestRequest(BaseModel):
    git_url: str
    branch: str = Field(default="main")
    auth_token: str | None = Field(default=None)

class IngestResponse(BaseModel):
    job_id: str
    status: str
    repo_id: str | None = None

# Global Kafka producer
producer: KafkaProducer | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global producer
    producer = KafkaProducer(settings.kafka_bootstrap_servers)
    await producer.start()
    logger.info("Ingestion service starting", extra={"kafka": settings.kafka_bootstrap_servers})

    # Ensure storage path exists
    os.makedirs(settings.repo_storage_path, exist_ok=True)

    yield

    await producer.stop()
    logger.info("Ingestion service shutting down")

app = FastAPI(title="Ingestion Service", version="1.0.0", lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "ingestion"}

async def _process_ingestion(job_id: str, repo_id: str, req: IngestRequest):
    """Background task: clone repo, extract commit, emit event."""
    session: AsyncSession = AsyncSessionLocal()
    try:
        # Determine storage path
        safe_name = req.git_url.replace(":", "_").replace("/", "_")
        dest_path = os.path.join(settings.repo_storage_path, f"{safe_name}_{repo_id}")

        # Clone repository
        commit_hash = clone_repository(
            req.git_url, dest_path, req.branch, req.auth_token
        )

        # Update DB
        await session.execute(
            update(RepoORM)
            .where(RepoORM.id == repo_id)
            .values(
                commit_hash=commit_hash,
                status="ingested",
                storage_path=dest_path,
                updated_at=datetime.utcnow(),
            )
        )
        await session.commit()

        # Emit Kafka event
        event = {
            "specversion": "1.0",
            "type": "repo.ingested",
            "source": "ingestion-service",
            "id": job_id,
            "time": datetime.utcnow().isoformat() + "Z",
            "datacontenttype": "application/json",
            "data": {
                "repo_id": repo_id,
                "url": req.git_url,
                "branch": req.branch,
                "commit": commit_hash,
                "storage_path": dest_path,
            },
        }
        await producer.send("repo.ingested", event, key=repo_id)
        logger.info(
            "Repo ingested and event emitted",
            extra={"repo_id": repo_id, "commit": commit_hash},
        )
    except Exception as exc:
        logger.exception("Ingestion failed", extra={"repo_id": repo_id})
        await session.execute(
            update(RepoORM)
            .where(RepoORM.id == repo_id)
            .values(status="failed", updated_at=datetime.utcnow())
        )
        await session.commit()
    finally:
        await session.close()

@app.post("/repos", response_model=IngestResponse, status_code=202)
async def ingest_repo(
    req: IngestRequest,
    background: BackgroundTasks,
    session: AsyncSession = Depends(get_db),
):
    job_id = str(uuid.uuid4())
    repo_id = str(uuid.uuid4())

    # Insert pending record
    repo = RepoORM(
        id=repo_id,
        url=req.git_url,
        branch=req.branch,
        status="pending",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(repo)
    await session.commit()

    background.add_task(_process_ingestion, job_id, repo_id, req)

    return IngestResponse(job_id=job_id, status="queued", repo_id=repo_id)

@app.get("/repos/{repo_id}")
async def get_repo(repo_id: str, session: AsyncSession = Depends(get_db)):
    result = await session.execute(
        select(RepoORM).where(RepoORM.id == repo_id)
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Repo not found")
    return {
        "id": row.id,
        "url": row.url,
        "branch": row.branch,
        "commit_hash": row.commit_hash,
        "status": row.status,
        "storage_path": row.storage_path,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
