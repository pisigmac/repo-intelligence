"""API Gateway with Phase 2 routing."""
import os
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Repo Intelligence Gateway", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8082"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

QUERY_URL = os.getenv("QUERY_SERVICE_URL", "http://query-service:8080")
EXECUTION_URL = os.getenv("EXECUTION_SERVICE_URL", "http://execution-service:8080")
INGESTION_URL = os.getenv("INGESTION_SERVICE_URL", "http://ingestion-service:8080")
FEEDBACK_URL = os.getenv("FEEDBACK_SERVICE_URL", "http://feedback-service:8080")
APPROVAL_URL = os.getenv("APPROVAL_SERVICE_URL", "http://approval-service:8080")
KNOWLEDGE_URL = os.getenv("KNOWLEDGE_SERVICE_URL", "http://knowledge-service:8080")
AGENT_URL = os.getenv("AGENT_ORCHESTRATOR_URL", "http://agent-orchestrator:8080")

client = httpx.AsyncClient(timeout=30.0)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "gateway", "version": "2.0.0"}

# Phase 1 routes
@app.post("/repos")
async def ingest_repo(request: Request):
    body = await request.json()
    resp = await client.post(f"{INGESTION_URL}/repos", json=body)
    return JSONResponse(status_code=resp.status_code, content=resp.json())

@app.get("/repos/{repo_id}")
async def get_repo(repo_id: str):
    resp = await client.get(f"{INGESTION_URL}/repos/{repo_id}")
    return JSONResponse(status_code=resp.status_code, content=resp.json())

@app.get("/capabilities")
async def list_capabilities(request: Request):
    params = dict(request.query_params)
    resp = await client.get(f"{QUERY_URL}/capabilities", params=params)
    return JSONResponse(status_code=resp.status_code, content=resp.json())

@app.get("/playbooks")
async def list_playbooks(request: Request):
    params = dict(request.query_params)
    resp = await client.get(f"{QUERY_URL}/playbooks", params=params)
    return JSONResponse(status_code=resp.status_code, content=resp.json())

@app.post("/query")
async def query(request: Request):
    body = await request.json()
    resp = await client.post(f"{QUERY_URL}/query", json=body)
    return JSONResponse(status_code=resp.status_code, content=resp.json())

@app.post("/execute")
async def execute(request: Request):
    body = await request.json()
    resp = await client.post(f"{EXECUTION_URL}/execute", json=body)
    return JSONResponse(status_code=resp.status_code, content=resp.json())

@app.get("/parse/{repo_id}")
async def get_parse(repo_id: str):
    resp = await client.get(f"http://parser-service:8080/parse/{repo_id}")
    return JSONResponse(status_code=resp.status_code, content=resp.json())

# Phase 2 routes
@app.post("/feedback")
async def submit_feedback(request: Request):
    body = await request.json()
    resp = await client.post(f"{FEEDBACK_URL}/feedback", json=body)
    return JSONResponse(status_code=resp.status_code, content=resp.json())

@app.get("/feedback/{playbook_id}/metrics")
async def get_metrics(playbook_id: str):
    resp = await client.get(f"{FEEDBACK_URL}/feedback/{playbook_id}/metrics")
    return JSONResponse(status_code=resp.status_code, content=resp.json())

@app.get("/playbooks/{playbook_id}/versions")
async def get_versions(playbook_id: str):
    # Query playbooks table for versions
    resp = await client.get(f"{QUERY_URL}/playbooks?capability_id={playbook_id}")
    return JSONResponse(status_code=resp.status_code, content=resp.json())

@app.post("/playbooks/{playbook_id}/transfer")
async def transfer_playbook(playbook_id: str, request: Request):
    body = await request.json()
    resp = await client.post(f"{KNOWLEDGE_URL}/playbooks/{playbook_id}/transfer", json=body)
    return JSONResponse(status_code=resp.status_code, content=resp.json())

@app.get("/approvals")
async def list_approvals(request: Request):
    params = dict(request.query_params)
    resp = await client.get(f"{APPROVAL_URL}/approvals", params=params)
    return JSONResponse(status_code=resp.status_code, content=resp.json())

@app.post("/approvals/{approval_id}/decision")
async def submit_approval(approval_id: str, request: Request):
    body = await request.json()
    resp = await client.post(f"{APPROVAL_URL}/approvals/{approval_id}/decision", json=body)
    return JSONResponse(status_code=resp.status_code, content=resp.json())

@app.get("/approvals/{approval_id}/diff")
async def get_approval_diff(approval_id: str):
    resp = await client.get(f"{APPROVAL_URL}/approvals/{approval_id}/diff")
    return JSONResponse(status_code=resp.status_code, content=resp.json())

@app.post("/agents/execute")
async def agent_execute(request: Request):
    body = await request.json()
    resp = await client.post(f"{AGENT_URL}/agents/execute", json=body)
    return JSONResponse(status_code=resp.status_code, content=resp.json())

@app.post("/knowledge/search")
async def knowledge_search(request: Request):
    body = await request.json()
    resp = await client.post(f"{KNOWLEDGE_URL}/knowledge/search", json=body)
    return JSONResponse(status_code=resp.status_code, content=resp.json())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
