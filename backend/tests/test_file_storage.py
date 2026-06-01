import os
import shutil
import pytest
import zipfile
import io
from memory.file_storage import save_file, list_files, get_file_content, create_zip_archive, get_filename_for_agent

@pytest.mark.asyncio
async def test_filename_mapping():
    assert get_filename_for_agent("BackendAgent") == "backend.py"
    assert get_filename_for_agent("APIAgent") == "openapi.yaml"
    assert get_filename_for_agent("UnknownAgent") == "unknownagent_output.txt"

@pytest.mark.asyncio
async def test_file_operations():
    task_id = "test-task-123"
    agent_name = "BackendAgent"
    content = "print('Hello World')"

    # 1. Save file
    saved_path = await save_file(task_id, agent_name, content)
    if saved_path.startswith("gs://"):
        assert True
    else:
        assert os.path.exists(saved_path)

    # 2. List files
    files = await list_files(task_id)
    assert len(files) > 0
    assert any(f["name"] == "backend.py" for f in files)

    # 3. Get content
    retrieved_content = await get_file_content(task_id, "backend.py")
    assert retrieved_content == content

    # 4. Create ZIP
    zip_stream = await create_zip_archive(task_id)
    assert zip_stream is not None
    
    # Read zip content
    with zipfile.ZipFile(zip_stream, "r") as z:
        namelist = z.namelist()
        assert "backend.py" in namelist
        assert z.read("backend.py").decode("utf-8") == content

    # Cleanup local folder
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "workspace"))
    task_dir = os.path.join(base_dir, task_id)
    if os.path.exists(task_dir):
        shutil.rmtree(task_dir)
