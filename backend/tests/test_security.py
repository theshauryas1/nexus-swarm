import pytest
from fastapi.testclient import TestClient
from main import app
from routes import active_tasks
from memory.file_storage import secure_path

client = TestClient(app)

def test_rate_limiting():
    # Make multiple requests to a rate-limited endpoint (/files/task_id/download)
    # Limit is 5/minute, so the 6th request should fail with HTTP 429
    task_id = "test-limit-task-id"
    for i in range(5):
        response = client.get(f"/files/{task_id}/download")
        # Might be 404/500/200 depending on environment/mock setup, but not 429
        assert response.status_code != 429
    
    # 6th request should trigger rate limit (429)
    response = client.get(f"/files/{task_id}/download")
    assert response.status_code == 429
    assert "Retry-After" in response.headers
    assert int(response.headers["Retry-After"]) > 0

def test_secure_path_helper():
    # Safe paths
    base = "C:\\workspace"
    assert secure_path(base, "task-1", "file.py").endswith("file.py")
    
    # Unsafe path traversals
    with pytest.raises(PermissionError):
        secure_path(base, "..", "passwd")
        
    with pytest.raises(PermissionError):
        secure_path(base, "task-1", "..", "..", "config.py")

def test_directory_traversal_api():
    # Verify that traversal attempts are rejected either by FastAPI/Starlette normalization (404)
    # or by our secure_path checks (400)
    response = client.get("/files/../../etc/passwd")
    assert response.status_code in (400, 404)

    response = client.get("/files/test-task-id/..%2F..%2Fconfig.py")
    assert response.status_code in (400, 404)

def test_input_validation():
    # Title too long (max 100 characters)
    long_title = "A" * 101
    payload = {
        "title": long_title,
        "description": "Short desc"
    }
    response = client.post("/submit-task", json=payload)
    assert response.status_code == 400  # Pydantic validation error

    # Empty title (min 1 character)
    payload = {
        "title": "",
        "description": "Short desc"
    }
    response = client.post("/submit-task", json=payload)
    assert response.status_code == 400  # Pydantic validation error

    # Description too long (max 2000 characters)
    long_desc = "B" * 2001
    payload = {
        "title": "Valid Title",
        "description": long_desc
    }
    response = client.post("/submit-task", json=payload)
    assert response.status_code == 400  # Pydantic validation error

def test_input_sanitization():
    # Submit task with HTML tags to test XSS sanitization
    payload = {
        "title": "<script>alert('XSS')</script>",
        "description": "<b>Bold text</b>"
    }
    response = client.post("/submit-task", json=payload)
    assert response.status_code == 200
    task_id = response.json()["task_id"]

    # Verify task in active_tasks has escaped strings
    assert task_id in active_tasks
    saved_task = active_tasks[task_id]
    assert saved_task["title"] == "&lt;script&gt;alert(&#x27;XSS&#x27;)&lt;/script&gt;"

    # Clean up
    if task_id in active_tasks:
        del active_tasks[task_id]
