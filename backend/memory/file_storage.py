"""
NexusSwarm — GCS and Local File Storage Client
Saves agent outputs as files in a local workspace and/or Google Cloud Storage (GCS).
Provides listing, reading, and ZIP downloading.
"""

import io
import logging
import os
import zipfile
import boto3
from botocore.exceptions import ClientError

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
        if settings.s3_bucket:
            try:
                # Try initialization using optional credentials or default session credentials
                session_opts = {}
                if settings.aws_access_key_id:
                    session_opts["aws_access_key_id"] = settings.aws_access_key_id
                if settings.aws_secret_access_key:
                    session_opts["aws_secret_access_key"] = settings.aws_secret_access_key
                if settings.aws_region:
                    session_opts["region_name"] = settings.aws_region

                _storage_client = boto3.client("s3", **session_opts)
                logger.info("✅ S3 Client initialized successfully")
            except Exception as e:
                logger.warning("⚠️ Failed to initialize S3 Client: %s", e)
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
    Saves an agent output content to local filesystem AND Amazon S3 if enabled.
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

    # 2. Save to S3 if configured
    if settings.s3_bucket:
        try:
            client = get_storage_client()
            if client:
                client.put_object(
                    Bucket=settings.s3_bucket,
                    Key=f"{task_id}/{filename}",
                    Body=content.encode("utf-8"),
                    ContentType="text/plain",
                )
                logger.info("Uploaded to S3: s3://%s/%s/%s", settings.s3_bucket, task_id, filename)
                return f"s3://{settings.s3_bucket}/{task_id}/{filename}"
        except Exception as e:
            logger.error("❌ Failed to upload file to S3: %s", e)

    return local_path

async def list_files(task_id: str) -> list[dict]:
    """
    Lists all generated files for a given task.
    Returns a list of dicts: [{'name': 'backend.py', 'size': 123, 'lang': 'python'}]
    """
    settings = get_settings()
    files_list = []

    # If S3 bucket is enabled, read from S3 to ensure multi-replica consistency
    if settings.s3_bucket:
        try:
            client = get_storage_client()
            if client:
                response = client.list_objects_v2(
                    Bucket=settings.s3_bucket,
                    Prefix=f"{task_id}/",
                )
                if "Contents" in response:
                    for item in response["Contents"]:
                        key = item["Key"]
                        filename = os.path.basename(key)
                        if filename:
                            files_list.append({
                                "name": filename,
                                "size": item["Size"],
                                "lang": get_lang_for_filename(filename),
                            })
                if files_list:
                    return files_list
        except Exception as e:
            logger.error("Failed to list files from S3: %s", e)

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

    # Read from S3 first
    if settings.s3_bucket:
        try:
            client = get_storage_client()
            if client:
                response = client.get_object(
                    Bucket=settings.s3_bucket,
                    Key=f"{task_id}/{filename}",
                )
                return response["Body"].read().decode("utf-8")
        except Exception as e:
            logger.error("Failed to download file from S3: %s", e)

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
        if settings.s3_bucket:
            try:
                client = get_storage_client()
                if client:
                    response = client.list_objects_v2(
                        Bucket=settings.s3_bucket,
                        Prefix=f"{task_id}/",
                    )
                    if "Contents" in response:
                        for item in response["Contents"]:
                            key = item["Key"]
                            filename = os.path.basename(key)
                            if filename:
                                obj_resp = client.get_object(
                                    Bucket=settings.s3_bucket,
                                    Key=key,
                                )
                                content = obj_resp["Body"].read()
                                zip_file.writestr(filename, content)
                                files_added = True
            except Exception as e:
                logger.error("Failed to read files from S3 for ZIP: %s", e)

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
