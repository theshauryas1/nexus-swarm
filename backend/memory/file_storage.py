"""
NexusSwarm — GCS and Local File Storage Client
Saves agent outputs as files in a local workspace and/or Google Cloud Storage (GCS).
Provides listing, reading, and ZIP downloading.
"""

import io
import logging
import os
import zipfile
from google.cloud import storage

from config import get_settings

logger = logging.getLogger(__name__)

def secure_path(base_dir: str, *subpaths: str) -> str:
    """
    Safely resolve absolute path and prevent directory traversal.
    """
    abs_path = os.path.abspath(os.path.join(base_dir, *subpaths))
    abs_base = os.path.abspath(base_dir)
    if os.path.commonpath([abs_base, abs_path]) != abs_base:
        raise PermissionError("Directory traversal attempt detected")
    return abs_path

# Map agent names to IDE-style filenames
AGENT_FILE_MAP = {
    "BackendAgent": "backend.py",
    "APIAgent": "openapi.yaml",
    "FrontendAgent": "components.tsx",
    "TestAgent": "test_backend.py",
    "DeployAgent": "Dockerfile",
    "RepairAgent": "repair.py",
    "ScannerAgent": "security_report.json",
    "RequirementAgent": "requirements.md",
    "RiskAnalyzer": "risk_analysis.md",
    "HeadOrchestrator": "execution_plan.json",
    "KnowledgeMemoryAgent": "knowledge.md",
    "DiagnosticsAgent": "diagnostics.md",
}

# Monaco language mapper based on file extension
EXTENSION_LANG_MAP = {
    ".py": "python",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".tsx": "typescript",
    ".json": "json",
    ".md": "markdown",
    "Dockerfile": "dockerfile",
}

_storage_client = None

def get_storage_client():
    global _storage_client
    if _storage_client is None:
        settings = get_settings()
        if settings.gcs_bucket:
            try:
                opts = {}
                if settings.project_id:
                    opts["project"] = settings.project_id
                _storage_client = storage.Client(**opts)
                logger.info("✅ GCS Client initialized successfully")
            except Exception as e:
                logger.warning("⚠️ Failed to initialize GCS Client: %s", e)
                _storage_client = None
    return _storage_client

def get_filename_for_agent(agent_name: str) -> str:
    return AGENT_FILE_MAP.get(agent_name, f"{agent_name.lower()}_output.txt")

def get_lang_for_filename(filename: str) -> str:
    _, ext = os.path.splitext(filename)
    if filename == "Dockerfile":
        return "dockerfile"
    return EXTENSION_LANG_MAP.get(ext, "plaintext")

async def save_file(task_id: str, agent_name: str, content: str) -> str:
    """
    Saves an agent output content to local filesystem AND Google Cloud Storage (GCS) if enabled.
    Returns the file path or URI where it was saved.
    """
    filename = get_filename_for_agent(agent_name)
    settings = get_settings()

    # 1. Save locally (always, for terminal access / local workspace compatibility)
    # Put it inside /app/workspace/{task_id} or ./workspace/{task_id}
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "workspace"))
    local_path = secure_path(base_dir, task_id, filename)
    task_dir = os.path.dirname(local_path)
    os.makedirs(task_dir, exist_ok=True)
    
    with open(local_path, "w", encoding="utf-8") as f:
        f.write(content)
    logger.info("Saved local file: %s", local_path)

    # 2. Save to GCS if configured
    if settings.gcs_bucket:
        try:
            client = get_storage_client()
            if client:
                bucket = client.bucket(settings.gcs_bucket)
                blob = bucket.blob(f"{task_id}/{filename}")
                blob.upload_from_string(content, content_type="text/plain")
                logger.info("Uploaded to GCS: gs://%s/%s/%s", settings.gcs_bucket, task_id, filename)
                return f"gs://{settings.gcs_bucket}/{task_id}/{filename}"
        except Exception as e:
            logger.error("❌ Failed to upload file to GCS: %s", e)

    return local_path

async def list_files(task_id: str) -> list[dict]:
    """
    Lists all generated files for a given task.
    Returns a list of dicts: [{'name': 'backend.py', 'size': 123, 'lang': 'python'}]
    """
    settings = get_settings()
    files_list = []

    # If GCS bucket is enabled, read from GCS to ensure multi-replica consistency
    if settings.gcs_bucket:
        try:
            client = get_storage_client()
            if client:
                bucket = client.bucket(settings.gcs_bucket)
                blobs = bucket.list_blobs(prefix=f"{task_id}/")
                for blob in blobs:
                    filename = os.path.basename(blob.name)
                    if filename:
                        files_list.append({
                            "name": filename,
                            "size": blob.size or 0,
                            "lang": get_lang_for_filename(filename),
                        })
                if files_list:
                    return files_list
        except Exception as e:
            logger.error("Failed to list files from GCS: %s", e)

    # Fallback to local workspace files
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "workspace"))
    task_dir = secure_path(base_dir, task_id)
    if os.path.exists(task_dir):
        for filename in os.listdir(task_dir):
            file_path = secure_path(task_dir, filename)
            if os.path.isfile(file_path):
                files_list.append({
                    "name": filename,
                    "size": os.path.getsize(file_path),
                    "lang": get_lang_for_filename(filename),
                })
    
    return files_list

async def get_file_content(task_id: str, filename: str) -> str | None:
    """
    Retrieves content of a specific file for a task.
    """
    settings = get_settings()

    # Read from GCS first
    if settings.gcs_bucket:
        try:
            client = get_storage_client()
            if client:
                bucket = client.bucket(settings.gcs_bucket)
                blob = bucket.blob(f"{task_id}/{filename}")
                return blob.download_as_bytes().decode("utf-8")
        except Exception as e:
            logger.error("Failed to download file from GCS: %s", e)

    # Local fallback
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "workspace"))
    file_path = secure_path(base_dir, task_id, filename)
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    return None

async def create_zip_archive(task_id: str) -> io.BytesIO:
    """
    Creates a ZIP archive of all files for a task and returns a byte stream.
    """
    zip_buffer = io.BytesIO()
    settings = get_settings()
    files_added = False

    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        if settings.gcs_bucket:
            try:
                client = get_storage_client()
                if client:
                    bucket = client.bucket(settings.gcs_bucket)
                    blobs = bucket.list_blobs(prefix=f"{task_id}/")
                    for blob in blobs:
                        filename = os.path.basename(blob.name)
                        if filename:
                            content = blob.download_as_bytes()
                            zip_file.writestr(filename, content)
                            files_added = True
            except Exception as e:
                logger.error("Failed to read files from GCS for ZIP: %s", e)

        if not files_added:
            # Local fallback
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "workspace"))
            task_dir = secure_path(base_dir, task_id)
            if os.path.exists(task_dir):
                for filename in os.listdir(task_dir):
                    file_path = secure_path(task_dir, filename)
                    if os.path.isfile(file_path):
                        zip_file.write(file_path, filename)

    zip_buffer.seek(0)
    return zip_buffer
