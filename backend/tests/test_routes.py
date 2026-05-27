import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "NexusSwarm"

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

def test_agents():
    response = client.get("/agents")
    assert response.status_code == 200
    data = response.json()
    assert "agents" in data
    assert len(data["agents"]) > 0

def test_stats():
    response = client.get("/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_tasks" in data

def test_submit_task():
    # Submit task with mock payload
    payload = {
        "title": "Build a Simple Website",
        "description": "Create an index.html and style.css"
    }
    response = client.post("/submit-task", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert "task_id" in data
