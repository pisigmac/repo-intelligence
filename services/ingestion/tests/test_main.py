"""Tests for ingestion service."""
import pytest
from unittest.mock import patch, MagicMock
from service.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["service"] == "ingestion"


@patch("service.main.clone_repository")
@patch("service.main.KafkaProducer")
def test_ingest_repo(mock_kafka, mock_clone):
    mock_clone.return_value = "abc123"
    mock_producer = MagicMock()
    mock_kafka.return_value = mock_producer
    mock_producer.start = MagicMock(return_value=None)
    mock_producer.stop = MagicMock(return_value=None)
    mock_producer.send = MagicMock(return_value=None)

    response = client.post("/repos", json={
        "git_url": "https://github.com/test/repo.git",
        "branch": "main"
    })
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "queued"
    assert "repo_id" in data
