"""Approval Service: human-in-the-loop workflow for playbook improvements."""
import os
import sys
import json
import uuid
import asyncio
import logging
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, "/app")
from libs.common import configure_logging, get_settings, KafkaProducer, KafkaConsumer, AsyncSessionLocal

settings = get_settings()
logger = configure_logging(settings.app_name, settings.log_level)


class ApprovalDecision(BaseModel):
    decision: str  # approved, rejected
    reviewer_notes: str | None = None


class ApprovalResponse(BaseModel):
    approval_id: str
    playbook_id: str
    version: str
    status: str
    changes_summary: dict | None = None


# WebSocket connection manager for real-time notifications
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for conn in self.active_connections:
            try:
                await conn.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()


async def handle_playbook_improved(topic: str, message: dict):
    """Notify WebSocket clients when new approval is pending."""
    data = message.get("data", {})
    await manager.broadcast({
        "type": "new_approval",
        "playbook_id": data.get("improved_playbook_id"),
        "original_id": data.get("original_playbook_id"),
        "version": data.get("version"),
        "estimated_improvement": data.get("estimated_score_improvement"),
    })


producer: KafkaProducer | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global producer
    producer = KafkaProducer(settings.kafka_bootstrap_servers)
    await producer.start()

    consumer = KafkaConsumer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        topics=["playbook.improved"],
        group_id=f"{settings.kafka_group_id}-approval-notify",
        handler=handle_playbook_improved,
    )
    await consumer.start()
    task = asyncio.create_task(consumer.run())
    logger.info("Approval service started")

    yield

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    await consumer.stop()
    await producer.stop()

app = FastAPI(title="Approval Service", version="2.0.0", lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "approval"}

@app.get("/approvals")
async def list_approvals(status: str | None = None, limit: int = 20):
    session: AsyncSession = AsyncSessionLocal()
    try:
        sql = select(text("*")).select_from(text("approvals")).order_by(text("created_at DESC")).limit(limit)
        if status:
            sql = sql.where(text(f"status = '{status}'"))
        result = await session.execute(sql)
        rows = result.mappings().all()
        return [dict(r) for r in rows]
    finally:
        await session.close()

@app.get("/approvals/{approval_id}")
async def get_approval(approval_id: str):
    session: AsyncSession = AsyncSessionLocal()
    try:
        result = await session.execute(
            text("SELECT * FROM approvals WHERE id = :id"),
            {"id": approval_id}
        )
        row = result.mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="Approval not found")
        return dict(row)
    finally:
        await session.close()

@app.get("/approvals/{approval_id}/diff")
async def get_approval_diff(approval_id: str):
    """Return diff between original and improved playbook."""
    session: AsyncSession = AsyncSessionLocal()
    try:
        result = await session.execute(
            text("SELECT * FROM approvals WHERE id = :id"),
            {"id": approval_id}
        )
        approval = result.mappings().first()
        if not approval:
            raise HTTPException(status_code=404, detail="Approval not found")

        original_id = approval["original_playbook_id"]
        improved_id = approval["playbook_id"]

        orig = await session.execute(text("SELECT steps FROM playbooks WHERE id = :id"), {"id": original_id})
        imp = await session.execute(text("SELECT steps FROM playbooks WHERE id = :id"), {"id": improved_id})
        orig_steps = orig.mappings().first()
        imp_steps = imp.mappings().first()

        return {
            "approval_id": approval_id,
            "original_playbook_id": original_id,
            "improved_playbook_id": improved_id,
            "original_steps": json.loads(orig_steps["steps"]) if orig_steps else [],
            "improved_steps": json.loads(imp_steps["steps"]) if imp_steps else [],
            "changes_summary": approval["changes_summary"],
        }
    finally:
        await session.close()

@app.post("/approvals/{approval_id}/decision")
async def submit_decision(approval_id: str, decision: ApprovalDecision):
    session: AsyncSession = AsyncSessionLocal()
    try:
        result = await session.execute(
            text("SELECT * FROM approvals WHERE id = :id AND status = 'pending'"),
            {"id": approval_id}
        )
        approval = result.mappings().first()
        if not approval:
            raise HTTPException(status_code=404, detail="Pending approval not found")

        new_status = decision.decision
        if new_status not in ("approved", "rejected"):
            raise HTTPException(status_code=400, detail="Decision must be 'approved' or 'rejected'")

        await session.execute(
            text("""
                UPDATE approvals 
                SET status = :status, approved_by = :reviewer, reviewer_notes = :notes, decided_at = NOW()
                WHERE id = :id
            """),
            {
                "status": new_status,
                "reviewer": decision.reviewer_notes or "manual",
                "notes": decision.reviewer_notes,
                "id": approval_id,
            }
        )
        await session.commit()

        playbook_id = approval["playbook_id"]

        if new_status == "approved":
            # Update playbook status to approved
            await session.execute(
                text("UPDATE playbooks SET status = 'approved' WHERE id = :id"),
                {"id": playbook_id}
            )
            await session.commit()

            # Emit approved event
            event = {
                "specversion": "1.0",
                "type": "playbook.approved",
                "source": "approval-service",
                "id": str(uuid.uuid4()),
                "time": datetime.utcnow().isoformat() + "Z",
                "datacontenttype": "application/json",
                "data": {
                    "playbook_id": playbook_id,
                    "version": approval["version"],
                    "original_playbook_id": approval["original_playbook_id"],
                    "approved_by": decision.reviewer_notes or "manual",
                },
            }
            await producer.send("playbook.approved", event, key=playbook_id)
            logger.info("Playbook approved", extra={"playbook_id": playbook_id})
        else:
            # Mark as rejected
            await session.execute(
                text("UPDATE playbooks SET status = 'rejected' WHERE id = :id"),
                {"id": playbook_id}
            )
            await session.commit()
            logger.info("Playbook rejected", extra={"playbook_id": playbook_id})

        await manager.broadcast({
            "type": "decision_update",
            "approval_id": approval_id,
            "playbook_id": playbook_id,
            "status": new_status,
        })

        return {"status": "ok", "decision": new_status, "playbook_id": playbook_id}
    finally:
        await session.close()

@app.websocket("/ws/approvals")
async def websocket_approvals(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive, client can ping
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
