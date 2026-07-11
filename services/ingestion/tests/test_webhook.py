import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from services.ingestion.main import app

client = TestClient(app)

@patch("services.ingestion.main._process_ingestion")
@patch("libs.common.db.AsyncSessionLocal")
def test_github_webhook_push_event(mock_session, mock_process_ingestion):
    # Mocking the session
    mock_db_session = MagicMock()
    mock_session.return_value = mock_db_session
    
    payload = {
        "ref": "refs/heads/feature-branch",
        "repository": {
            "clone_url": "https://github.com/test/repo.git"
        }
    }
    
    headers = {
        "X-GitHub-Event": "push"
    }
    
    response = client.post("/webhooks/github", json=payload, headers=headers)
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "queued"
    assert "job_id" in data
    assert "repo_id" in data

def test_github_webhook_ping_event():
    headers = {
        "X-GitHub-Event": "ping"
    }
    response = client.post("/webhooks/github", json={}, headers=headers)
    assert response.status_code == 202
    assert response.json() == {"status": "pong"}

def test_github_webhook_ignored_event():
    headers = {
        "X-GitHub-Event": "pull_request"
    }
    response = client.post("/webhooks/github", json={}, headers=headers)
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "ignored"

def test_github_webhook_missing_url():
    payload = {
        "ref": "refs/heads/main",
        "repository": {}
    }
    headers = {
        "X-GitHub-Event": "push"
    }
    response = client.post("/webhooks/github", json=payload, headers=headers)
    assert response.status_code == 400
    assert "Missing repository clone_url" in response.json()["detail"]
