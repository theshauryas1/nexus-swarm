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


def test_search_memory_endpoint():
    from memory.db_client import _MOCK_MEMORIES
    _MOCK_MEMORIES.clear()
    _MOCK_MEMORIES.append({
        "id": "mock-id-123",
        "content": "Use Helmet in Express for secure headers.",
        "embedding": [0.1] * 1024,
        "memory_type": "security_standard",
        "source_task_id": None,
        "confidence_score": 1.0,
        "access_count": 0,
        "created_at": None,
        "updated_at": None
    })
    
    response = client.get("/memory/search?q=Helmet+headers")
    assert response.status_code == 200
    data = response.json()
    assert "query" in data
    assert len(data["results"]) > 0
    assert data["results"][0]["content"] == "Use Helmet in Express for secure headers."

def test_models_performance_endpoint():
    response = client.get("/models/performance")
    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "NVIDIA NIM"
    assert "metrics" in data

def test_benchmark_endpoint():
    payload = {
        "task_type": "code_generation",
        "requirements": {
            "max_latency_ms": 1500,
            "min_success_rate": 80.0
        }
    }
    response = client.post("/models/benchmark", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["task_type"] == "code_generation"
    assert "selected_model" in data

