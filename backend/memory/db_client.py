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

import builtins
builtins._use_mock_db = False
builtins.logging = logging

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
_MOCK_EVALUATIONS = []
_MOCK_BENCHMARKS = []
_MOCK_MEMORIES = []
_MOCK_MODEL_PERFORMANCE = {}


def get_engine():
    global _engine, _use_mock_db
    if _engine is None:
        settings = get_settings()
        if not settings.database_url:
            _use_mock_db = True
            logging.getLogger(__name__).warning("DATABASE_URL is not configured. Using in-memory Mock Database.")
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
    import logging
    global _use_mock_db
    try:
        if _use_mock_db:
            yield None
            return
    except NameError as ne:
        import sys
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"NameError: _use_mock_db undefined! Globals keys: {list(globals().keys())}")
        logger.error(f"__file__ is: {__file__}")
        try:
            with open(__file__, "r", encoding="utf-8") as f:
                logger.error(f"File content: {f.read(2000)}")
        except Exception as e:
            logger.error(f"Failed to read __file__: {e}")
        raise ne
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
        logging.getLogger(__name__).warning("⚠️ Falling back to in-memory Mock Database")
        yield None


async def ping_db() -> bool:
    import logging
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
        logging.getLogger(__name__).warning("⚠️ PostgreSQL not reachable. Falling back to in-memory Mock Database.")
        return False


async def close_db() -> None:
    global _engine
    if _engine:
        try:
            await _engine.dispose()
        except Exception:
            pass
        _engine = None
        logging.getLogger(__name__).info("Database connection closed")


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


# ═══════════════════════════════════════════════════════════════
#  EVALUATION OPERATIONS
# ═══════════════════════════════════════════════════════════════

class EvaluationDB:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_evaluation(
        self,
        task_id: str,
        agent_name: str,
        accuracy_score: float,
        completeness_score: float,
        security_score: float,
        maintainability_score: float,
        scalability_score: float,
        overall_score: float,
        strengths: list,
        weaknesses: list,
    ) -> int:
        if _use_mock_db:
            eval_id = len(_MOCK_EVALUATIONS) + 1
            _MOCK_EVALUATIONS.append({
                "id": eval_id,
                "task_id": task_id,
                "agent_name": agent_name,
                "accuracy_score": accuracy_score,
                "completeness_score": completeness_score,
                "security_score": security_score,
                "maintainability_score": maintainability_score,
                "scalability_score": scalability_score,
                "overall_score": overall_score,
                "strengths": strengths,
                "weaknesses": weaknesses,
                "created_at": datetime.now()
            })
            return eval_id

        import json
        result = await self.session.execute(
            text("""
                INSERT INTO evaluations (
                    task_id, agent_name, accuracy_score, completeness_score,
                    security_score, maintainability_score, scalability_score,
                    overall_score, strengths, weaknesses
                ) VALUES (
                    :task_id, :agent_name, :accuracy_score, :completeness_score,
                    :security_score, :maintainability_score, :scalability_score,
                    :overall_score, :strengths, :weaknesses
                ) RETURNING id
            """),
            {
                "task_id": task_id,
                "agent_name": agent_name,
                "accuracy_score": accuracy_score,
                "completeness_score": completeness_score,
                "security_score": security_score,
                "maintainability_score": maintainability_score,
                "scalability_score": scalability_score,
                "overall_score": overall_score,
                "strengths": json.dumps(strengths),
                "weaknesses": json.dumps(weaknesses),
            }
        )
        await self.session.commit()
        return result.scalar()

    async def get_evaluations(self, task_id: str) -> list[dict]:
        if _use_mock_db:
            return [e for e in _MOCK_EVALUATIONS if e["task_id"] == task_id]

        result = await self.session.execute(
            text("SELECT * FROM evaluations WHERE task_id = :task_id ORDER BY created_at DESC"),
            {"task_id": task_id}
        )
        return [dict(row) for row in result.mappings()]


# ═══════════════════════════════════════════════════════════════
#  BENCHMARK OPERATIONS
# ═══════════════════════════════════════════════════════════════

class BenchmarkDB:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_benchmark_result(
        self,
        benchmark_name: str,
        task_id: str,
        pass_status: bool,
        score: float,
        execution_time: float,
        repair_iterations: int = 0,
        failure_reason: str | None = None,
        root_cause: str | None = None,
        recovery_success: bool | None = None,
        estimated_cost: float = 0.0,
        total_tokens: int = 0,
    ) -> int:
        if _use_mock_db:
            bench_id = len(_MOCK_BENCHMARKS) + 1
            _MOCK_BENCHMARKS.append({
                "id": bench_id,
                "benchmark_name": benchmark_name,
                "task_id": task_id,
                "pass": pass_status,
                "score": score,
                "execution_time": execution_time,
                "repair_iterations": repair_iterations,
                "failure_reason": failure_reason,
                "root_cause": root_cause,
                "recovery_success": recovery_success,
                "estimated_cost": estimated_cost,
                "total_tokens": total_tokens,
                "created_at": datetime.now()
            })
            return bench_id

        result = await self.session.execute(
            text("""
                INSERT INTO benchmark_results (
                    benchmark_name, task_id, pass, score, execution_time,
                    repair_iterations, failure_reason, root_cause, recovery_success,
                    estimated_cost, total_tokens
                ) VALUES (
                    :benchmark_name, :task_id, :pass_status, :score, :execution_time,
                    :repair_iterations, :failure_reason, :root_cause, :recovery_success,
                    :estimated_cost, :total_tokens
                ) RETURNING id
            """),
            {
                "benchmark_name": benchmark_name,
                "task_id": task_id,
                "pass_status": pass_status,
                "score": score,
                "execution_time": execution_time,
                "repair_iterations": repair_iterations,
                "failure_reason": failure_reason,
                "root_cause": root_cause,
                "recovery_success": recovery_success,
                "estimated_cost": estimated_cost,
                "total_tokens": total_tokens,
            }
        )
        await self.session.commit()
        return result.scalar()

    async def get_benchmark_results(self, limit: int = 100) -> list[dict]:
        if _use_mock_db:
            return sorted(_MOCK_BENCHMARKS, key=lambda b: b["created_at"], reverse=True)[:limit]

        result = await self.session.execute(
            text("""
                SELECT br.*, t.title as task_title, t.status as task_status
                FROM benchmark_results br
                LEFT JOIN tasks t ON br.task_id = t.id
                ORDER BY br.created_at DESC LIMIT :limit
            """),
            {"limit": limit}
        )
        return [dict(row) for row in result.mappings()]

    async def get_benchmark_stats(self) -> dict:
        if _use_mock_db:
            total = len(_MOCK_BENCHMARKS)
            if total == 0:
                return {
                    "total_benchmarks": 0,
                    "success_rate": 0.0,
                    "avg_score": 0.0,
                    "repair_success_rate": 0.0,
                    "security_pass_rate": 0.0,
                    "hallucination_trap_defense_rate": 0.0,
                    "adversarial_defense_rate": 0.0,
                    "avg_cost": 0.0,
                    "max_cost": 0.0,
                    "total_tokens": 0,
                }
            passed = sum(1 for b in _MOCK_BENCHMARKS if b.get("pass", b.get("pass_status", False)))
            avg_score = sum(b["score"] for b in _MOCK_BENCHMARKS) / total
            success_rate = (passed / total) * 100

            # Adversarial defense: separate category
            adv = [b for b in _MOCK_BENCHMARKS if "[ADVERSARIAL]" in b.get("benchmark_name", "").upper()]
            adv_blocked = sum(1 for b in adv if b.get("pass", b.get("pass_status", False)))
            adversarial_defense_rate = (adv_blocked / len(adv)) * 100 if adv else 0.0

            # Hallucination trap defense: tasks that did NOT trigger a known trap
            halluc = [b for b in _MOCK_BENCHMARKS if "[HALLUCINATION]" in b.get("benchmark_name", "").upper()]
            trap_ok = sum(1 for b in halluc if b.get("root_cause", "") != "hallucination_trap_triggered")
            halluc_trap_rate = (trap_ok / len(halluc)) * 100 if halluc else 0.0

            # Repair success rate: tasks with repair_iterations > 0 that passed
            repaired = [b for b in _MOCK_BENCHMARKS if b.get("repair_iterations", 0) > 0]
            repair_success = sum(1 for b in repaired if b.get("pass", b.get("pass_status", False)))
            repair_success_rate = (repair_success / len(repaired)) * 100 if repaired else 0.0
            
            # LLMOps metrics
            avg_cost = sum(b.get("estimated_cost", 0.0) for b in _MOCK_BENCHMARKS) / total
            max_cost = max((b.get("estimated_cost", 0.0) for b in _MOCK_BENCHMARKS), default=0.0)
            total_tokens = sum(b.get("total_tokens", 0) for b in _MOCK_BENCHMARKS)

            return {
                "total_benchmarks": total,
                "success_rate": round(success_rate, 1),
                "avg_score": round(avg_score, 2),
                "repair_success_rate": round(repair_success_rate, 1),
                "security_pass_rate": 0.0,  # not tracked in mock
                "hallucination_trap_defense_rate": round(halluc_trap_rate, 1),
                "adversarial_defense_rate": round(adversarial_defense_rate, 1),
                "avg_cost": round(avg_cost, 4),
                "max_cost": round(max_cost, 4),
                "total_tokens": int(total_tokens),
            }

        # ── Real DB stats ──────────────────────────────────────────
        result = await self.session.execute(text("""
            SELECT
                COUNT(*)::float                                                      AS total_benchmarks,
                COALESCE(AVG(score), 0.0)::float                                     AS avg_score,
                COALESCE(
                    (COUNT(*) FILTER (WHERE pass = true)::float / NULLIF(COUNT(*), 0)) * 100,
                    0.0
                )                                                                    AS success_rate,
                COALESCE(
                    (COUNT(*) FILTER (WHERE repair_iterations > 0 AND pass = true)::float /
                     NULLIF(COUNT(*) FILTER (WHERE repair_iterations > 0), 0)) * 100,
                    0.0
                )                                                                    AS repair_success_rate,
                COALESCE(
                    (COUNT(*) FILTER (
                        WHERE benchmark_name ILIKE '[ADVERSARIAL]%' AND pass = true
                    )::float / NULLIF(COUNT(*) FILTER (
                        WHERE benchmark_name ILIKE '[ADVERSARIAL]%'
                    ), 0)) * 100,
                    0.0
                )                                                                    AS adversarial_defense_rate,
                COALESCE(
                    (COUNT(*) FILTER (
                        WHERE benchmark_name ILIKE '[HALLUCINATION]%'
                        AND (root_cause IS NULL OR root_cause != 'hallucination_trap_triggered')
                    )::float / NULLIF(COUNT(*) FILTER (
                        WHERE benchmark_name ILIKE '[HALLUCINATION]%'
                    ), 0)) * 100,
                    0.0
                )                                                                    AS hallucination_trap_defense_rate,
                COALESCE(AVG(estimated_cost), 0.0)::float                             AS avg_cost,
                COALESCE(MAX(estimated_cost), 0.0)::float                             AS max_cost,
                COALESCE(SUM(total_tokens), 0)::bigint                                AS total_tokens
            FROM benchmark_results
        """))
        stats = dict(result.mappings().one())

        # Security pass rate: from evaluations table
        sec_result = await self.session.execute(text("""
            SELECT
                COALESCE(
                    (COUNT(*) FILTER (WHERE security_score >= 8.0)::float / NULLIF(COUNT(*), 0)) * 100,
                    0.0
                ) AS security_pass_rate
            FROM evaluations
        """))
        sec_stats = dict(sec_result.mappings().one())

        return {
            "total_benchmarks": int(stats.get("total_benchmarks") or 0),
            "success_rate": round(float(stats.get("success_rate") or 0.0), 1),
            "avg_score": round(float(stats.get("avg_score") or 0.0), 2),
            "repair_success_rate": round(float(stats.get("repair_success_rate") or 0.0), 1),
            "security_pass_rate": round(float(sec_stats.get("security_pass_rate") or 0.0), 1),
            "adversarial_defense_rate": round(float(stats.get("adversarial_defense_rate") or 0.0), 1),
            "hallucination_trap_defense_rate": round(float(stats.get("hallucination_trap_defense_rate") or 0.0), 1),
            "avg_cost": round(float(stats.get("avg_cost") or 0.0), 4),
            "max_cost": round(float(stats.get("max_cost") or 0.0), 4),
            "total_tokens": int(stats.get("total_tokens") or 0),
        }



class MemoryDB:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_memory(
        self,
        content: str,
        memory_type: str,
        embedding: list[float] | None = None,
        source_task_id: str | None = None,
        confidence_score: float = 1.0,
    ) -> str:
        if _use_mock_db or self.session is None:
            import uuid
            memory_id = str(uuid.uuid4())
            _MOCK_MEMORIES.append({
                "id": memory_id,
                "content": content,
                "embedding": embedding,
                "memory_type": memory_type,
                "source_task_id": source_task_id,
                "confidence_score": confidence_score,
                "access_count": 0,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            })
            return memory_id

        emb_val = None
        if embedding:
            emb_val = "[" + ",".join(map(str, embedding)) + "]"
        
        result = await self.session.execute(
            text("""
                INSERT INTO memories (content, embedding, memory_type, source_task_id, confidence_score)
                VALUES (:content, :embedding, :memory_type, :source_task_id, :confidence_score)
                RETURNING id
            """),
            {
                "content": content,
                "embedding": emb_val,
                "memory_type": memory_type,
                "source_task_id": source_task_id,
                "confidence_score": confidence_score,
            }
        )
        await self.session.commit()
        return str(result.scalar())

    async def semantic_search(self, query_embedding: list[float], limit: int = 5) -> list[dict]:
        if _use_mock_db or self.session is None:
            if not _MOCK_MEMORIES:
                return []
            
            def cosine_similarity(v1, v2):
                if not v1 or not v2 or len(v1) != len(v2):
                    return 0.0
                import math
                dot = sum(a * b for a, b in zip(v1, v2))
                norm1 = math.sqrt(sum(a * a for a in v1))
                norm2 = math.sqrt(sum(b * b for b in v2))
                if norm1 == 0 or norm2 == 0:
                    return 0.0
                return dot / (norm1 * norm2)

            scored = []
            for m in _MOCK_MEMORIES:
                sim = cosine_similarity(query_embedding, m["embedding"]) if m["embedding"] else 0.0
                scored.append((m, sim))
            
            scored.sort(key=lambda x: x[1], reverse=True)
            results = []
            for m, sim in scored[:limit]:
                m["access_count"] += 1
                res = m.copy()
                res["similarity"] = sim
                results.append(res)
            return results

        # Fallback query if pgvector fails: we select all and compute or use standard vector operators
        # Check if vector extension is enabled by running standard query. If it fails, fallback to keyword or list matching
        try:
            emb_val = "[" + ",".join(map(str, query_embedding)) + "]"
            result = await self.session.execute(
                text("""
                    SELECT id, content, memory_type, source_task_id, confidence_score, access_count, created_at,
                           (1 - (embedding <=> :query_embedding::vector)) AS similarity
                    FROM memories
                    WHERE embedding IS NOT NULL
                    ORDER BY embedding <=> :query_embedding::vector
                    LIMIT :limit
                """),
                {"query_embedding": emb_val, "limit": limit}
            )
            rows = [dict(row) for row in result.mappings()]
            if rows:
                ids = [row["id"] for row in rows]
                await self.session.execute(
                    text("UPDATE memories SET access_count = access_count + 1 WHERE id = ANY(:ids)"),
                    {"ids": ids}
                )
                await self.session.commit()
            return rows
        except Exception as e:
            logger.warning("pgvector search failed, falling back to simple retrieval: %s", e)
            result = await self.session.execute(
                text("SELECT id, content, memory_type, source_task_id, confidence_score, access_count, created_at FROM memories LIMIT :limit"),
                {"limit": limit}
            )
            rows = [dict(row) for row in result.mappings()]
            for r in rows:
                r["similarity"] = 0.5 # Default fallback similarity
            return rows

    async def list_memories(self, memory_type: str | None = None, limit: int = 20) -> list[dict]:
        if _use_mock_db or self.session is None:
            memories = _MOCK_MEMORIES
            if memory_type:
                memories = [m for m in memories if m["memory_type"] == memory_type]
            memories = sorted(memories, key=lambda m: m["created_at"], reverse=True)
            return memories[:limit]

        try:
            if memory_type:
                result = await self.session.execute(
                    text("SELECT id, content, memory_type, source_task_id, confidence_score, access_count, created_at FROM memories WHERE memory_type = :memory_type ORDER BY created_at DESC LIMIT :limit"),
                    {"memory_type": memory_type, "limit": limit}
                )
            else:
                result = await self.session.execute(
                    text("SELECT id, content, memory_type, source_task_id, confidence_score, access_count, created_at FROM memories ORDER BY created_at DESC LIMIT :limit"),
                    {"limit": limit}
                )
            return [dict(row) for row in result.mappings()]
        except Exception as e:
            logger.warning("Failed to query memories from DB, falling back to mock: %s", e)
            memories = _MOCK_MEMORIES
            if memory_type:
                memories = [m for m in memories if m["memory_type"] == memory_type]
            return memories[:limit]


class ModelPerformanceDB:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def log_performance(
        self,
        model_name: str,
        task_type: str,
        latency_ms: float,
        success: bool,
        cost_per_token: float = 0.0
    ) -> None:
        if _use_mock_db or self.session is None:
            key = (model_name, task_type)
            if key not in _MOCK_MODEL_PERFORMANCE:
                _MOCK_MODEL_PERFORMANCE[key] = {
                    "model_name": model_name,
                    "task_type": task_type,
                    "success_rate": 100.0 if success else 0.0,
                    "avg_latency_ms": latency_ms,
                    "hallucination_rate": 0.0,
                    "cost_per_token": cost_per_token,
                    "last_updated": datetime.now(),
                    "total_calls": 1,
                    "success_calls": 1 if success else 0
                }
            else:
                p = _MOCK_MODEL_PERFORMANCE[key]
                p["total_calls"] += 1
                if success:
                    p["success_calls"] += 1
                p["success_rate"] = (p["success_calls"] / p["total_calls"]) * 100.0
                p["avg_latency_ms"] = (p["avg_latency_ms"] * (p["total_calls"] - 1) + latency_ms) / p["total_calls"]
                p["cost_per_token"] = cost_per_token
                p["last_updated"] = datetime.now()
            return

        success_val = 100.0 if success else 0.0
        await self.session.execute(
            text("""
                INSERT INTO model_performance (model_name, task_type, success_rate, avg_latency_ms, cost_per_token, last_updated)
                VALUES (:model_name, :task_type, :success_rate, :avg_latency_ms, :cost_per_token, NOW())
                ON CONFLICT (model_name, task_type) DO UPDATE SET
                    success_rate = (model_performance.success_rate * 0.9) + (:success_rate * 0.1),
                    avg_latency_ms = (model_performance.avg_latency_ms * 0.9) + (:avg_latency_ms * 0.1),
                    cost_per_token = :cost_per_token,
                    last_updated = NOW()
            """),
            {
                "model_name": model_name,
                "task_type": task_type,
                "success_rate": success_val,
                "avg_latency_ms": latency_ms,
                "cost_per_token": cost_per_token,
            }
        )
        await self.session.commit()

    async def get_performance(self, model_name: str, task_type: str) -> dict | None:
        if _use_mock_db or self.session is None:
            return _MOCK_MODEL_PERFORMANCE.get((model_name, task_type))

        try:
            result = await self.session.execute(
                text("SELECT * FROM model_performance WHERE model_name = :model_name AND task_type = :task_type"),
                {"model_name": model_name, "task_type": task_type}
            )
            row = result.mappings().first()
            return dict(row) if row else None
        except Exception as e:
            logger.warning("Failed to query model_performance from DB, falling back to mock: %s", e)
            return _MOCK_MODEL_PERFORMANCE.get((model_name, task_type))

    async def list_performances(self) -> list[dict]:
        if _use_mock_db or self.session is None:
            return list(_MOCK_MODEL_PERFORMANCE.values())

        try:
            result = await self.session.execute(
                text("SELECT * FROM model_performance ORDER BY last_updated DESC")
            )
            return [dict(row) for row in result.mappings()]
        except Exception as e:
            logger.warning("Failed to query model_performance from DB, falling back to mock: %s", e)
            return list(_MOCK_MODEL_PERFORMANCE.values())



async def init_db_tables() -> None:
    """Ensure evaluations, benchmark_results, memories and model_performance tables exist."""
    global _use_mock_db
    if _use_mock_db:
        return
    try:
        factory = get_session_factory()
        if factory is None:
            return
        async with factory() as session:
            # Create evaluations
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS evaluations (
                    id                      SERIAL PRIMARY KEY,
                    task_id                 UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                    agent_name              VARCHAR(100) NOT NULL,
                    accuracy_score          DOUBLE PRECISION,
                    completeness_score      DOUBLE PRECISION,
                    security_score          DOUBLE PRECISION,
                    maintainability_score   DOUBLE PRECISION,
                    scalability_score       DOUBLE PRECISION,
                    overall_score           DOUBLE PRECISION,
                    strengths               JSONB DEFAULT '[]',
                    weaknesses              JSONB DEFAULT '[]',
                    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """))
            # Create benchmark_results
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS benchmark_results (
                    id                      SERIAL PRIMARY KEY,
                    benchmark_name          VARCHAR(255) NOT NULL,
                    task_id                 UUID REFERENCES tasks(id) ON DELETE SET NULL,
                    pass                    BOOLEAN NOT NULL DEFAULT FALSE,
                    score                   DOUBLE PRECISION,
                    execution_time          DOUBLE PRECISION,
                    repair_iterations       INTEGER DEFAULT 0,
                    failure_reason          TEXT,
                    root_cause              TEXT,
                    recovery_success        BOOLEAN,
                    estimated_cost          DOUBLE PRECISION DEFAULT 0.0,
                    total_tokens            INTEGER DEFAULT 0,
                    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """))
            
            # Create memories table (try pgvector first, fallback to standard TEXT)
            await session.commit()
            try:
                await session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                await session.execute(text("""
                    CREATE TABLE IF NOT EXISTS memories (
                        id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        content             TEXT NOT NULL,
                        embedding           vector(1024),
                        memory_type         TEXT NOT NULL,
                        source_task_id      UUID REFERENCES tasks(id) ON DELETE SET NULL,
                        confidence_score    DOUBLE PRECISION DEFAULT 1.0,
                        access_count        INTEGER DEFAULT 0,
                        created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                """))
            except Exception as e:
                logger.warning("Could not initialize memories table with pgvector, trying fallback: %s", e)
                await session.rollback()
                await session.execute(text("""
                    CREATE TABLE IF NOT EXISTS memories (
                        id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        content             TEXT NOT NULL,
                        embedding           TEXT,
                        memory_type         TEXT NOT NULL,
                        source_task_id      UUID REFERENCES tasks(id) ON DELETE SET NULL,
                        confidence_score    DOUBLE PRECISION DEFAULT 1.0,
                        access_count        INTEGER DEFAULT 0,
                        created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                """))

            # Create model_performance table
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS model_performance (
                    id                  SERIAL PRIMARY KEY,
                    model_name          TEXT NOT NULL,
                    task_type           TEXT NOT NULL,
                    success_rate        DOUBLE PRECISION DEFAULT 100.0,
                    avg_latency_ms      DOUBLE PRECISION DEFAULT 0.0,
                    hallucination_rate  DOUBLE PRECISION DEFAULT 0.0,
                    cost_per_token      DOUBLE PRECISION DEFAULT 0.0,
                    last_updated        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    CONSTRAINT uq_model_task UNIQUE (model_name, task_type)
                )
            """))
            
            # Apply ALTER TABLE migrations dynamically if columns do not exist
            for col, col_type in [
                ("repair_iterations", "INTEGER DEFAULT 0"),
                ("failure_reason", "TEXT"),
                ("root_cause", "TEXT"),
                ("recovery_success", "BOOLEAN"),
                ("estimated_cost", "DOUBLE PRECISION DEFAULT 0.0"),
                ("total_tokens", "INTEGER DEFAULT 0")
            ]:
                try:
                    await session.execute(text(f"ALTER TABLE benchmark_results ADD COLUMN IF NOT EXISTS {col} {col_type}"))
                except Exception as ex:
                    logger.warning(f"Could not dynamically add column {col} to benchmark_results: {ex}")
            # Create indexes
            await session.execute(text("CREATE INDEX IF NOT EXISTS idx_evaluations_task_id ON evaluations(task_id)"))
            await session.execute(text("CREATE INDEX IF NOT EXISTS idx_benchmark_results_task_id ON benchmark_results(task_id)"))
            await session.commit()
            logger.info("✅ Database tables evaluations & benchmark_results initialized successfully")
    except Exception as e:
        logger.error("❌ Failed to initialize database tables: %s", e)
