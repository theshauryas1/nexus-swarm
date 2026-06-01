import pytest
from fastapi.testclient import TestClient
from main import app
from routes import active_tasks

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

def test_submit_task_with_parent():
    # Submit task with a parent_task_id in payload
    payload = {
        "title": "Add Contact Page",
        "description": "Add a contact form to the existing simple website.",
        "parent_task_id": "test-parent-uuid-123"
    }
    response = client.post("/submit-task", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert "task_id" in data
    
    task_id = data["task_id"]
    assert task_id in active_tasks
    assert active_tasks[task_id]["parent_task_id"] == "test-parent-uuid-123"
    
    # Cleanup
    if task_id in active_tasks:
        del active_tasks[task_id]
