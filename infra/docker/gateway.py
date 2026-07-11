"""API Gateway with Phase 2 routing and Local/GitHub Auth."""
import os
import httpx

from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from libs.auth_module import GitHubAuthenticator, AuthRouter, get_password_hash, schemas

app = FastAPI(title="Repo Intelligence Gateway", version="2.0.0")

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:8090").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

QUERY_URL = os.getenv("QUERY_SERVICE_URL", "http://query-service:8080")
EXECUTION_URL = os.getenv("EXECUTION_SERVICE_URL", "http://execution-service:8080")
INGESTION_URL = os.getenv("INGESTION_SERVICE_URL", "http://ingestion-service:8080")
PARSER_URL = os.getenv("PARSER_SERVICE_URL", "http://parser-service:8080")
FEEDBACK_URL = os.getenv("FEEDBACK_SERVICE_URL", "http://feedback-service:8080")
APPROVAL_URL = os.getenv("APPROVAL_SERVICE_URL", "http://approval-service:8080")
KNOWLEDGE_URL = os.getenv("KNOWLEDGE_SERVICE_URL", "http://knowledge-service:8080")
AGENT_URL = os.getenv("AGENT_ORCHESTRATOR_URL", "http://agent-orchestrator:8080")

# --- Dummy Database for Local Auth ---
_users_db = {}

async def get_user_by_email(email: str):
    return _users_db.get(email)

async def create_user(user_in: schemas.UserCreate):
    user_dict = {
        "email": user_in.email,
        "hashed_password": get_password_hash(user_in.password),
        "is_active": True,
        "is_verified": False,
        "id": user_in.email,
    }
    _users_db[user_in.email] = user_dict
    return user_dict

def get_hashed_password_cb(user: dict):
    return user.get("hashed_password")

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "super-secret-default-key")

# --- Setup Universal Auth Modules ---
# 1. Local Auth
local_auth = AuthRouter(
    secret_key=JWT_SECRET_KEY,
    get_user_by_email=get_user_by_email,
    create_user=create_user,
    get_hashed_password=get_hashed_password_cb,
    algorithm="HS256"
)
app.include_router(local_auth.router)

# 2. GitHub Auth
github_auth = GitHubAuthenticator(
    client_id=os.getenv("GITHUB_CLIENT_ID", ""),
    client_secret=os.getenv("GITHUB_CLIENT_SECRET", ""),
    jwt_secret=JWT_SECRET_KEY,
    backend_callback_url="http://localhost:8000/auth/github/callback",
    frontend_callback_url="http://localhost:5173/auth/callback"
)
app.include_router(github_auth.router, prefix="/auth/github", tags=["auth"])

# Expose /auth/me for GitHub users specifically if needed, but local_auth already provides /auth/me!
# We will use local_auth.get_current_user_factory for all endpoints, which verifies the JWT correctly for both.
get_current_user = local_auth.get_current_user_factory()

client = httpx.AsyncClient(timeout=30.0)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "gateway", "version": "2.0.0"}

# --- Phase 1 routes ---
@app.post("/repos")
async def ingest_repo(request: Request, user: dict = Depends(get_current_user)):
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
async def execute(request: Request, user: dict = Depends(get_current_user)):
    body = await request.json()
    resp = await client.post(f"{EXECUTION_URL}/execute", json=body)
    return JSONResponse(status_code=resp.status_code, content=resp.json())

@app.get("/parse/{repo_id}")
async def get_parse(repo_id: str):
    resp = await client.get(f"{PARSER_URL}/parse/{repo_id}")
    return JSONResponse(status_code=resp.status_code, content=resp.json())

# --- Phase 2 routes ---
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
    resp = await client.get(f"{QUERY_URL}/playbooks?capability_id={playbook_id}")
    return JSONResponse(status_code=resp.status_code, content=resp.json())

@app.post("/playbooks/{playbook_id}/transfer")
async def transfer_playbook(playbook_id: str, request: Request, user: dict = Depends(get_current_user)):
    body = await request.json()
    resp = await client.post(f"{KNOWLEDGE_URL}/playbooks/{playbook_id}/transfer", json=body)
    return JSONResponse(status_code=resp.status_code, content=resp.json())

@app.get("/approvals")
async def list_approvals(request: Request):
    params = dict(request.query_params)
    resp = await client.get(f"{APPROVAL_URL}/approvals", params=params)
    return JSONResponse(status_code=resp.status_code, content=resp.json())

@app.post("/approvals/{approval_id}/decision")
async def submit_approval(approval_id: str, request: Request, user: dict = Depends(get_current_user)):
    body = await request.json()
    resp = await client.post(f"{APPROVAL_URL}/approvals/{approval_id}/decision", json=body)
    return JSONResponse(status_code=resp.status_code, content=resp.json())

@app.get("/approvals/{approval_id}/diff")
async def get_approval_diff(approval_id: str):
    resp = await client.get(f"{APPROVAL_URL}/approvals/{approval_id}/diff")
    return JSONResponse(status_code=resp.status_code, content=resp.json())

@app.post("/agents/execute")
async def agent_execute(request: Request, user: dict = Depends(get_current_user)):
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
