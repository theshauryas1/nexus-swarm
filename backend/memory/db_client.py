"""
NexusSwarm — PostgreSQL Database Client
Async SQLAlchemy — task CRUD, agent logs, pipeline health
"""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import get_settings

logger = logging.getLogger(__name__)

# ─── Engine ──────────────────────────────────────────────────────
_engine = None
_session_factory = None
_use_mock_db = False

# In-memory Mock DB Storage
_MOCK_TASKS = {}
_MOCK_PIPELINES = {}
_MOCK_LOGS = []
_MOCK_OUTPUTS = []
_MOCK_CONFLICTS = {}


def get_engine():
    global _engine, _use_mock_db
    if _engine is None:
        settings = get_settings()
        if not settings.database_url:
            _use_mock_db = True
            logger.warning("DATABASE_URL is not configured. Using in-memory Mock Database.")
            return None
        _engine = create_async_engine(
            settings.database_url,
            echo=settings.app_env == "development",
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
        )
    return _engine


def get_session_factory():
    global _session_factory
    if _session_factory is None:
        engine = get_engine()
        if engine is None:
            return None
        _session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def get_db_session() -> AsyncSession:
    global _use_mock_db
    if _use_mock_db:
        yield None
        return
    try:
        factory = get_session_factory()
        if factory is None:
            _use_mock_db = True
            yield None
            return
        async with factory() as session:
            yield session
    except Exception:
        _use_mock_db = True
        logger.warning("⚠️ Falling back to in-memory Mock Database")
        yield None


async def ping_db() -> bool:
    global _use_mock_db
    try:
        factory = get_session_factory()
        if factory is None:
            _use_mock_db = True
            return False
        async with factory() as session:
            await session.execute(text("SELECT 1"))
        _use_mock_db = False
        return True
    except Exception:
        _use_mock_db = True
        logger.warning("⚠️ PostgreSQL not reachable. Falling back to in-memory Mock Database.")
        return False


async def close_db() -> None:
    global _engine
    if _engine:
        try:
            await _engine.dispose()
        except Exception:
            pass
        _engine = None
        logger.info("Database connection closed")


# ═══════════════════════════════════════════════════════════════
#  TASK OPERATIONS
# ═══════════════════════════════════════════════════════════════

class TaskDB:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_task(
        self,
        title: str,
        description: str,
        priority: int = 1,
        parent_task_id: str | None = None,
    ) -> dict:
        metadata = {}
        if parent_task_id:
            metadata["parent_task_id"] = parent_task_id

        if _use_mock_db:
            import uuid
            task_id = str(uuid.uuid4())
            task = {
                "id": task_id,
                "title": title,
                "description": description,
                "status": "pending",
                "priority": priority,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "completed_at": None,
                "metadata": metadata
            }
            _MOCK_TASKS[task_id] = task
            return task

        import json
        result = await self.session.execute(
            text("""
                INSERT INTO tasks (title, description, priority, metadata)
                VALUES (:title, :description, :priority, :metadata)
                RETURNING id, title, description, status, priority, created_at, updated_at, metadata
            """),
            {"title": title, "description": description, "priority": priority, "metadata": json.dumps(metadata)},
        )
        await self.session.commit()
        row = result.mappings().one()
        return dict(row)

    async def get_task(self, task_id: str) -> dict | None:
        if _use_mock_db:
            return _MOCK_TASKS.get(task_id)

        result = await self.session.execute(
            text("SELECT * FROM tasks WHERE id = :id"),
            {"id": task_id},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def update_task_status(self, task_id: str, status: str) -> None:
        if _use_mock_db:
            if task_id in _MOCK_TASKS:
                _MOCK_TASKS[task_id]["status"] = status
                _MOCK_TASKS[task_id]["updated_at"] = datetime.now()
                if status in ("complete", "failed"):
                    _MOCK_TASKS[task_id]["completed_at"] = datetime.now()
            return

        if status in ("complete", "failed"):
            await self.session.execute(
                text("UPDATE tasks SET status = :status, completed_at = NOW(), updated_at = NOW() WHERE id = :id"),
                {"status": status, "id": task_id},
            )
        else:
            await self.session.execute(
                text("UPDATE tasks SET status = :status, updated_at = NOW() WHERE id = :id"),
                {"status": status, "id": task_id},
            )
        await self.session.commit()

    async def list_tasks(self, limit: int = 20, offset: int = 0) -> list[dict]:
        if _use_mock_db:
            tasks = sorted(_MOCK_TASKS.values(), key=lambda t: t["created_at"], reverse=True)
            return tasks[offset : offset + limit]

        result = await self.session.execute(
            text("SELECT * FROM tasks ORDER BY created_at DESC LIMIT :limit OFFSET :offset"),
            {"limit": limit, "offset": offset},
        )
        return [dict(row) for row in result.mappings()]

    async def get_stats(self) -> dict:
        if _use_mock_db:
            total = len(_MOCK_TASKS)
            active = sum(1 for t in _MOCK_TASKS.values() if t["status"] not in ("complete", "failed"))
            completed = sum(1 for t in _MOCK_TASKS.values() if t["status"] == "complete")
            failed = sum(1 for t in _MOCK_TASKS.values() if t["status"] == "failed")
            return {
                "total_tasks": total,
                "active_tasks": active,
                "completed_tasks": completed,
                "failed_tasks": failed
            }

        result = await self.session.execute(text("""
            SELECT
                COUNT(*) FILTER (WHERE TRUE)                    AS total_tasks,
                COUNT(*) FILTER (WHERE status NOT IN ('complete','failed')) AS active_tasks,
                COUNT(*) FILTER (WHERE status = 'complete')     AS completed_tasks,
                COUNT(*) FILTER (WHERE status = 'failed')       AS failed_tasks
            FROM tasks
        """))
        return dict(result.mappings().one())


# ═══════════════════════════════════════════════════════════════
#  PIPELINE OPERATIONS
# ═══════════════════════════════════════════════════════════════

class PipelineDB:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_pipelines_for_task(self, task_id: str) -> None:
        """Create all 5 pipeline rows for a new task."""
        if _use_mock_db:
            pipelines = [
                ("planning",    "PlanningManager"),
                ("engineering", "EngineeringManager"),
                ("qa",          "QAManager"),
                ("security",    "SecurityManager"),
                ("devops",      "DevOpsManager"),
            ]
            for name, manager in pipelines:
                _MOCK_PIPELINES[(task_id, name)] = {
                    "task_id": task_id,
                    "name": name,
                    "manager_agent": manager,
                    "status": "idle",
                    "progress": 0,
                    "started_at": None,
                    "completed_at": None,
                    "error_message": None,
                    "updated_at": datetime.now()
                }
            return

        pipelines = [
            ("planning",    "PlanningManager"),
            ("engineering", "EngineeringManager"),
            ("qa",          "QAManager"),
            ("security",    "SecurityManager"),
            ("devops",      "DevOpsManager"),
        ]
        for name, manager in pipelines:
            await self.session.execute(
                text("""
                    INSERT INTO pipelines (task_id, name, manager_agent)
                    VALUES (:task_id, :name, :manager_agent)
                    ON CONFLICT DO NOTHING
                """),
                {"task_id": task_id, "name": name, "manager_agent": manager},
            )
        await self.session.commit()

    async def update_pipeline(
        self,
        task_id: str,
        pipeline_name: str,
        status: str,
        progress: int = None,
        error_message: str = None,
    ) -> None:
        if _use_mock_db:
            key = (task_id, pipeline_name)
            if key in _MOCK_PIPELINES:
                p = _MOCK_PIPELINES[key]
                p["status"] = status
                p["updated_at"] = datetime.now()
                if progress is not None:
                    p["progress"] = progress
                if status == "active" and not p["started_at"]:
                    p["started_at"] = datetime.now()
                if status in ("done", "failed"):
                    p["completed_at"] = datetime.now()
                if error_message:
                    p["error_message"] = error_message
            return

        updates = ["status = :status", "updated_at = NOW()"]
        params = {"task_id": task_id, "name": pipeline_name, "status": status}

        if progress is not None:
            updates.append("progress = :progress")
            params["progress"] = progress

        if status == "active":
            updates.append("started_at = COALESCE(started_at, NOW())")

        if status in ("done", "failed"):
            updates.append("completed_at = NOW()")

        if error_message:
            updates.append("error_message = :error_message")
            params["error_message"] = error_message

        await self.session.execute(
            text(f"UPDATE pipelines SET {', '.join(updates)} WHERE task_id = :task_id AND name = :name"),
            params,
        )
        await self.session.commit()

    async def get_pipelines(self, task_id: str) -> list[dict]:
        if _use_mock_db:
            return [p for p in _MOCK_PIPELINES.values() if p["task_id"] == task_id]

        result = await self.session.execute(
            text("SELECT * FROM pipelines WHERE task_id = :task_id ORDER BY name"),
            {"task_id": task_id},
        )
        return [dict(row) for row in result.mappings()]


# ═══════════════════════════════════════════════════════════════
#  AGENT LOG OPERATIONS
# ═══════════════════════════════════════════════════════════════

class AgentLogDB:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def log_event(
        self,
        agent_name: str,
        agent_level: str,
        event_type: str,
        message: str,
        status: str = "in_progress",
        task_id: str = None,
        pipeline_name: str = None,
        parent_manager: str = None,
        payload: dict = None,
    ) -> int:
        if _use_mock_db:
            log_id = len(_MOCK_LOGS) + 1
            _MOCK_LOGS.append({
                "id": log_id,
                "task_id": task_id,
                "pipeline_name": pipeline_name,
                "agent_name": agent_name,
                "agent_level": agent_level,
                "parent_manager": parent_manager,
                "event_type": event_type,
                "message": message,
                "status": status,
                "payload": payload or {},
                "created_at": datetime.now()
            })
            return log_id

        result = await self.session.execute(
            text("""
                INSERT INTO agent_logs
                    (task_id, pipeline_name, agent_name, agent_level,
                     parent_manager, event_type, message, status, payload)
                VALUES
                    (:task_id, :pipeline_name, :agent_name, :agent_level,
                     :parent_manager, :event_type, :message, :status, :payload::jsonb)
                RETURNING id
            """),
            {
                "task_id":       task_id,
                "pipeline_name": pipeline_name,
                "agent_name":    agent_name,
                "agent_level":   agent_level,
                "parent_manager": parent_manager,
                "event_type":    event_type,
                "message":       message,
                "status":        status,
                "payload":       str(payload or {}),
            },
        )
        await self.session.commit()
        return result.scalar()

    async def get_logs(
        self, task_id: str = None, limit: int = 100, offset: int = 0
    ) -> list[dict]:
        if _use_mock_db:
            logs = [l for l in _MOCK_LOGS if not task_id or l["task_id"] == task_id]
            logs = sorted(logs, key=lambda l: l["created_at"], reverse=True)
            return logs[offset : offset + limit]

        if task_id:
            result = await self.session.execute(
                text("""
                    SELECT * FROM agent_logs WHERE task_id = :task_id
                    ORDER BY created_at DESC LIMIT :limit OFFSET :offset
                """),
                {"task_id": task_id, "limit": limit, "offset": offset},
            )
        else:
            result = await self.session.execute(
                text("SELECT * FROM agent_logs ORDER BY created_at DESC LIMIT :limit OFFSET :offset"),
                {"limit": limit, "offset": offset},
            )
        return [dict(row) for row in result.mappings()]

    async def get_log_count(self) -> int:
        if _use_mock_db:
            return len(_MOCK_LOGS)

        result = await self.session.execute(text("SELECT COUNT(*) FROM agent_logs"))
        return result.scalar()


# ═══════════════════════════════════════════════════════════════
#  OUTPUT OPERATIONS
# ═══════════════════════════════════════════════════════════════

class OutputDB:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_output(
        self,
        task_id: str,
        output_type: str,
        pipeline_name: str,
        content: str,
        file_path: str = None,
    ) -> str:
        if _use_mock_db:
            output_id = str(len(_MOCK_OUTPUTS) + 1)
            _MOCK_OUTPUTS.append({
                "id": output_id,
                "task_id": task_id,
                "output_type": output_type,
                "pipeline_name": pipeline_name,
                "content": content,
                "file_path": file_path,
                "created_at": datetime.now()
            })
            return output_id

        result = await self.session.execute(
            text("""
                INSERT INTO task_outputs (task_id, output_type, pipeline_name, content, file_path)
                VALUES (:task_id, :output_type, :pipeline_name, :content, :file_path)
                RETURNING id
            """),
            {
                "task_id":       task_id,
                "output_type":   output_type,
                "pipeline_name": pipeline_name,
                "content":       content,
                "file_path":     file_path,
            },
        )
        await self.session.commit()
        return str(result.scalar())

    async def get_outputs(self, task_id: str) -> list[dict]:
        if _use_mock_db:
            return [o for o in _MOCK_OUTPUTS if o["task_id"] == task_id]

        result = await self.session.execute(
            text("SELECT * FROM task_outputs WHERE task_id = :task_id ORDER BY created_at"),
            {"task_id": task_id},
        )
        return [dict(row) for row in result.mappings()]


# ═══════════════════════════════════════════════════════════════
#  CONFLICT OPERATIONS
# ═══════════════════════════════════════════════════════════════

class ConflictDB:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_conflict(
        self, task_id: str, raised_by: str, blocked_by: str, reason: str
    ) -> str:
        if _use_mock_db:
            conflict_id = str(len(_MOCK_CONFLICTS) + 1)
            _MOCK_CONFLICTS[conflict_id] = {
                "id": conflict_id,
                "task_id": task_id,
                "raised_by": raised_by,
                "blocked_by": blocked_by,
                "reason": reason,
                "status": "pending",
                "resolution": None,
                "created_at": datetime.now(),
                "resolved_at": None
            }
            return conflict_id

        result = await self.session.execute(
            text("""
                INSERT INTO conflicts (task_id, raised_by, blocked_by, reason)
                VALUES (:task_id, :raised_by, :blocked_by, :reason)
                RETURNING id
            """),
            {"task_id": task_id, "raised_by": raised_by, "blocked_by": blocked_by, "reason": reason},
        )
        await self.session.commit()
        return str(result.scalar())

    async def resolve_conflict(self, conflict_id: str, resolution: str) -> None:
        if _use_mock_db:
            if conflict_id in _MOCK_CONFLICTS:
                c = _MOCK_CONFLICTS[conflict_id]
                c["status"] = "resolved"
                c["resolution"] = resolution
                c["resolved_at"] = datetime.now()
            return

        await self.session.execute(
            text("""
                UPDATE conflicts
                SET status = 'resolved', resolution = :resolution, resolved_at = NOW()
                WHERE id = :id
            """),
            {"id": conflict_id, "resolution": resolution},
        )
        await self.session.commit()

    async def get_conflicts(self, task_id: str) -> list[dict]:
        if _use_mock_db:
            return [c for c in _MOCK_CONFLICTS.values() if c["task_id"] == task_id]

        result = await self.session.execute(
            text("SELECT * FROM conflicts WHERE task_id = :task_id ORDER BY created_at"),
            {"task_id": task_id},
        )
        return [dict(row) for row in result.mappings()]

    async def get_conflict_count(self) -> int:
        if _use_mock_db:
            return len(_MOCK_CONFLICTS)

        result = await self.session.execute(text("SELECT COUNT(*) FROM conflicts"))
        return result.scalar()
