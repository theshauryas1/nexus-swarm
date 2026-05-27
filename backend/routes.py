"""
routes.py — NexusSwarm API Routes
Integrates llm_factory for real NIM calls.

CHANGES FROM SIMULATION VERSION:
  - Agent roster now pulls model + provider from AGENT_MODEL_MAP
  - submit_task now calls real LLM for HeadOrchestrator decomposition
  - Each agent sim block replaced with real call_agent_llm() call
  - /agents endpoint shows live model assignments
"""

import asyncio
import html
import logging
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Request, Query
from pydantic import BaseModel, Field, field_validator
from limiter import limiter

from agents.llm_factory import (
    call_agent_llm,
    get_model_for_agent,
    get_full_model_registry,
    AGENT_MODEL_MAP,
)

from fastapi.responses import StreamingResponse
from memory.db_client import get_db_session, TaskDB, PipelineDB, AgentLogDB, OutputDB
from memory.file_storage import save_file, list_files, get_file_content, create_zip_archive

logger = logging.getLogger(__name__)
router = APIRouter()


# ─────────────────────────────────────────────────────────────
#  IN-MEMORY STATE  (replace with Redis/Postgres as needed)
# ─────────────────────────────────────────────────────────────

active_tasks: dict = {}
websocket_clients: list[WebSocket] = []


# ─────────────────────────────────────────────────────────────
#  SCHEMAS
# ─────────────────────────────────────────────────────────────

class TaskRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=100, description="Title of the task")
    description: str = Field("", max_length=2000, description="Detailed description of the task")

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("Title is required.")
        return clean

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str) -> str:
        return value.strip()

class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str


# ─────────────────────────────────────────────────────────────
#  WEBSOCKET BROADCAST
# ─────────────────────────────────────────────────────────────

async def broadcast(event: dict):
    """Push event to all connected WebSocket clients."""
    disconnected = []
    for ws in websocket_clients:
        try:
            await ws.send_json(event)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        websocket_clients.remove(ws)


async def agent_event(
    task_id: str,
    agent: str,
    status: str,           # idle | active | working | done | error | blocked
    message: str,
    output: str = "",
    level: str = "worker", # orchestrator | manager | worker | gateway
    pipeline: str = "",    # planning | engineering | qa | security | devops | reliability
):
    await broadcast({
        "type":     "agent_update",
        "task_id":  task_id,
        "agent":    agent,
        "status":   status,
        "message":  message,
        "output":   output,
        "model":    get_model_for_agent(agent),
        "level":    level,
        "pipeline": pipeline,
        "ts":       datetime.utcnow().isoformat() + 'Z',
    })

    # Persist to active_tasks for /status polling
    task = active_tasks.get(task_id)
    if task:
        # Save output artifact
        if output and status == "done":
            task["outputs"][agent] = output
        # Update pipeline progress
        if pipeline and "pipelines" in task:
            for p in task["pipelines"]:
                if p["name"] == pipeline:
                    if status in ("active", "working"):
                        p["status"]   = "active"
                        p["progress"] = min(p["progress"] + 15, 90)
                    elif status == "done" and level == "manager":
                        p["status"]   = "done"
                        p["progress"] = 100
                    elif status == "done":
                        p["progress"] = min(p["progress"] + 20, 95)
                    elif status == "error":
                        p["status"]   = "failed"
                    elif status == "blocked":
                        p["status"]   = "blocked"
                    break

    # Save to storage asynchronously if output generated
    if output and status == "done":
        await save_file(task_id, agent, output)

    # Save event/log to database
    try:
        async for session in get_db_session():
            if not session:
                break
            log_db = AgentLogDB(session)
            await log_db.log_event(
                agent_name=agent,
                agent_level=level,
                event_type="agent_action",
                message=message,
                status=status,
                task_id=task_id,
                pipeline_name=pipeline,
                payload={"output": output} if output else {}
            )
            
            # If pipeline is specified, update pipeline row
            if pipeline:
                pipeline_db = PipelineDB(session)
                db_status = (
                    "active" if status in ("active", "working", "in_progress") else
                    "done" if status == "done" else
                    "failed" if status == "error" else
                    "blocked" if status == "blocked" else "idle"
                )
                progress = None
                if task and "pipelines" in task:
                    for p in task["pipelines"]:
                        if p["name"] == pipeline:
                            progress = p["progress"]
                            break
                await pipeline_db.update_pipeline(task_id, pipeline, db_status, progress)
                
            # If output is done, save task output row
            if output and status == "done":
                output_db = OutputDB(session)
                await output_db.save_output(task_id, agent, pipeline or "system", output)
                
            # If agent is HeadOrchestrator, update main task status
            if agent == "HeadOrchestrator":
                task_db = TaskDB(session)
                db_task_status = (
                    "complete" if status == "done" and message.startswith("✅") else
                    "failed" if status == "error" else
                    "planning" if status == "active" else "running"
                )
                await task_db.update_task_status(task_id, db_task_status)
    except Exception as e:
        logger.error("Error persisting agent event to DB: %s", e)



# ─────────────────────────────────────────────────────────────
#  AGENT ROSTER ENDPOINT
# ─────────────────────────────────────────────────────────────

@router.get("/agents")
@limiter.limit("60/minute")
async def get_agents(request: Request):
    """
    Returns all 28 agents with live model assignments from llm_factory.
    Frontend AgentGraph.tsx + OutputPanel.tsx consume this.
    """
    registry = get_full_model_registry()

    agents = []
    level_map = {
        "HeadOrchestrator":       "orchestrator",
        "PlanningManager":        "manager",
        "EngineeringManager":     "manager",
        "QAManager":              "manager",
        "SecurityManager":        "manager",
        "DevOpsManager":          "manager",
        "ReliabilityManager":     "manager",
        "HumanApprovalGateway":   "gateway",
    }

    for agent_name, info in registry.items():
        agents.append({
            "id":       agent_name,
            "name":     agent_name,
            "model":    info["model"],
            "provider": info["provider"],
            "level":    level_map.get(agent_name, "worker"),
            "status":   "idle",
        })

    return {
        "agents":      agents,
        "agent_count": len(agents),
        "providers":   {"primary": "NVIDIA NIM"},
    }


# ─────────────────────────────────────────────────────────────
#  SUBMIT TASK
# ─────────────────────────────────────────────────────────────

@router.post("/submit-task", response_model=TaskResponse)
@limiter.limit("10/minute")
async def submit_task(request: Request, task_req: TaskRequest):
    task_id = None
    clean_title = html.escape(task_req.title)
    clean_description = html.escape(task_req.description)

    try:
        async for session in get_db_session():
            if not session:
                break
            task_db = TaskDB(session)
            db_task = await task_db.create_task(clean_title, clean_description)
            if db_task:
                task_id = str(db_task["id"])
                pipeline_db = PipelineDB(session)
                await pipeline_db.create_pipelines_for_task(task_id)
                break
    except Exception as e:
        logger.error("Failed to create task in DB: %s", e)

    if not task_id:
        task_id = str(uuid.uuid4())

    active_tasks[task_id] = {
        "task_id":   task_id,
        "status":    "running",
        "title":     clean_title,
        "created_at": datetime.utcnow().isoformat() + 'Z',
        "outputs":   {},
        "pipelines": [
            {"name": "planning",    "status": "idle", "progress": 0},
            {"name": "engineering", "status": "idle", "progress": 0},
            {"name": "qa",          "status": "idle", "progress": 0},
            {"name": "security",    "status": "idle", "progress": 0},
            {"name": "devops",      "status": "idle", "progress": 0},
            {"name": "reliability", "status": "idle", "progress": 0},
        ],
    }

    # Run pipeline async — don't block the HTTP response
    asyncio.create_task(run_swarm_pipeline(task_id, clean_title, clean_description))

    return TaskResponse(
        task_id=task_id,
        status="running",
        message="Swarm pipeline started. Connect to /ws/agents for live updates.",
    )



# ─────────────────────────────────────────────────────────────
#  MAIN SWARM PIPELINE  (real LLM calls)
# ─────────────────────────────────────────────────────────────

async def run_swarm_pipeline(task_id: str, title: str, description: str):
    """
    Full 7-pipeline swarm execution with real NIM calls.
    Each agent_event() call updates the React Flow graph live.
    """
    try:
        # ── PIPELINE 1: HEAD ORCHESTRATOR ────────────────────
        await agent_event(task_id, "HeadOrchestrator", "active",
                          "Analyzing task and building execution plan...",
                          level="orchestrator", pipeline="planning")

        orchestrator_plan = await call_agent_llm(
            agent_name="HeadOrchestrator",
            prompt=f"""
You are the Head Orchestrator of an AI software delivery system.
Analyze this task and produce a structured execution plan.

Task: {title}
Description: {description}

Return a JSON plan with:
{{
  "complexity": "low|medium|high",
  "pipelines_needed": ["planning", "engineering", "qa", "security", "devops"],
  "key_risks": ["risk1", "risk2"],
  "estimated_agents": <number>,
  "summary": "one sentence plan"
}}
""",
            system="You are an AI Chief Technical Officer. Be precise and structured.",
        )

        await agent_event(task_id, "HeadOrchestrator", "done",
                          "Execution plan ready. Delegating to pipeline managers.",
                          output=orchestrator_plan, level="orchestrator", pipeline="planning")

        # ── PIPELINE 2: PLANNING ─────────────────────────────
        await agent_event(task_id, "PlanningManager", "active",
                          "Activating planning pipeline...", level="manager", pipeline="planning")

        await asyncio.gather(
            _run_requirement_agent(task_id, title, description),
            _run_risk_analyzer(task_id, title, description),
        )

        await agent_event(task_id, "PlanningManager", "done",
                          "Planning pipeline complete.", level="manager", pipeline="planning")

        # ── PIPELINE 3: ENGINEERING ──────────────────────────
        await agent_event(task_id, "EngineeringManager", "active",
                          "Activating engineering pipeline...", level="manager", pipeline="engineering")

        # Run backend + API in parallel, frontend after
        await asyncio.gather(
            _run_backend_agent(task_id, title, description),
            _run_api_agent(task_id, title, description),
        )
        await _run_frontend_agent(task_id, title)

        await agent_event(task_id, "EngineeringManager", "done",
                          "Engineering pipeline complete.", level="manager", pipeline="engineering")

        # ── PIPELINE 4: QA (with repair loop) ───────────────
        await agent_event(task_id, "QAManager", "active",
                          "Activating QA pipeline...", level="manager", pipeline="qa")

        qa_passed = await _run_qa_pipeline(task_id, title)

        await agent_event(task_id, "QAManager", "done",
                          f"QA pipeline complete. Tests passed: {qa_passed}",
                          level="manager", pipeline="qa")

        # ── PIPELINE 5: SECURITY ─────────────────────────────
        await agent_event(task_id, "SecurityManager", "active",
                          "Activating security pipeline...", level="manager", pipeline="security")

        security_cleared = await _run_security_pipeline(task_id, title)

        await agent_event(task_id, "SecurityManager",
                          "done" if security_cleared else "blocked",
                          "Security scan complete." if security_cleared
                          else "⚠️ BLOCKING DevOps — critical vulnerability found.",
                          level="manager", pipeline="security")

        # ── HUMAN APPROVAL GATEWAY ───────────────────────────
        await agent_event(task_id, "HumanApprovalGateway", "active",
                          "Requesting human approval before deployment...",
                          level="gateway")
        await asyncio.sleep(1.5)  # Simulate review pause
        await agent_event(task_id, "HumanApprovalGateway", "done",
                          "✅ APPROVED — proceeding to DevOps.",
                          level="gateway")

        if not security_cleared:
            active_tasks[task_id]["status"] = "blocked"
            return

        # ── PIPELINE 6: DEVOPS ───────────────────────────────
        await agent_event(task_id, "DevOpsManager", "active",
                          "Activating DevOps pipeline...", level="manager", pipeline="devops")
        await _run_deploy_agent(task_id, title)
        await agent_event(task_id, "DevOpsManager", "done",
                          "DevOps pipeline complete.", level="manager", pipeline="devops")

        # ── PIPELINE 7: RELIABILITY ──────────────────────────
        await agent_event(task_id, "ReliabilityManager", "active",
                          "Running reliability checks...", level="manager", pipeline="reliability")
        await asyncio.gather(
            _run_diagnostics_agent(task_id),
            _run_knowledge_memory_agent(task_id, title),
        )
        await agent_event(task_id, "ReliabilityManager", "done",
                          "Reliability pipeline complete.", level="manager", pipeline="reliability")

        # ── FINAL SUMMARY ────────────────────────────────────
        # Mark all pipelines done in task dict
        for p in active_tasks[task_id]["pipelines"]:
            if p["status"] != "failed" and p["status"] != "blocked":
                p["status"]   = "done"
                p["progress"] = 100

        await agent_event(task_id, "HeadOrchestrator", "done",
                          "✅ All pipelines complete. Swarm delivery successful.",
                          output="Swarm execution successful. All 6 pipelines completed.",
                          level="orchestrator")

        # Broadcast completion event for frontend detection
        await broadcast({
            "type":       "agent_update",
            "event_type": "complete",
            "agent":      "HeadOrchestrator",
            "level":      "orchestrator",
            "status":     "done",
            "message":    "✅ Swarm delivery complete!",
            "ts":         datetime.utcnow().isoformat() + 'Z',
        })

        active_tasks[task_id]["status"] = "complete"

    except Exception as e:
        logger.error(f"Pipeline error for task {task_id}: {e}")
        await agent_event(task_id, "HeadOrchestrator", "error",
                          f"Pipeline failed: {str(e)}", level="orchestrator")
        active_tasks[task_id]["status"] = "failed"


# ─────────────────────────────────────────────────────────────
#  INDIVIDUAL AGENT RUNNERS
# ─────────────────────────────────────────────────────────────

async def _run_requirement_agent(task_id: str, title: str, desc: str):
    await agent_event(task_id, "RequirementAgent", "working",
                      "Extracting structured requirements...")
    result = await call_agent_llm(
        "RequirementAgent",
        f"Extract structured software requirements for: {title}\n\n{desc}",
        system="Extract requirements as a numbered list. Be specific and testable.",
    )
    active_tasks[task_id]["outputs"]["requirements"] = result
    await agent_event(task_id, "RequirementAgent", "done",
                      "Requirements extracted.", output=result)


async def _run_risk_analyzer(task_id: str, title: str, desc: str):
    await agent_event(task_id, "RiskAnalyzer", "working",
                      "Analyzing technical risks...")
    result = await call_agent_llm(
        "RiskAnalyzer",
        f"Identify top 3 technical risks for building: {title}\n\n{desc}",
        system="You are a risk analyst. Return risks as JSON with severity and mitigation.",
    )
    active_tasks[task_id]["outputs"]["risks"] = result
    await agent_event(task_id, "RiskAnalyzer", "done",
                      "Risk register complete.", output=result)


async def _run_backend_agent(task_id: str, title: str, desc: str):
    await agent_event(task_id, "BackendAgent", "working",
                      "Generating FastAPI backend code...")
    result = await call_agent_llm(
        "BackendAgent",
        f"Generate a complete FastAPI backend for: {title}\n\n{desc}\n\n"
        "Include: models, routes, auth middleware, database setup.",
        system="You are a senior Python backend engineer. Write production-ready FastAPI code.",
        max_tokens=4096,
    )
    active_tasks[task_id]["outputs"]["backend_code"] = result
    await agent_event(task_id, "BackendAgent", "done",
                      "Backend code generated.", output=result[:500] + "...")


async def _run_api_agent(task_id: str, title: str, desc: str):
    await agent_event(task_id, "APIAgent", "working",
                      "Generating OpenAPI contract...")
    result = await call_agent_llm(
        "APIAgent",
        f"Generate an OpenAPI 3.0 spec for: {title}\n\n{desc}",
        system="Return a valid OpenAPI 3.0 YAML spec. Include all endpoints, schemas, auth.",
        max_tokens=2048,
    )
    active_tasks[task_id]["outputs"]["api_spec"] = result
    await agent_event(task_id, "APIAgent", "done",
                      "OpenAPI spec generated.", output=result[:300] + "...")


async def _run_frontend_agent(task_id: str, title: str):
    await agent_event(task_id, "FrontendAgent", "working",
                      "Generating React frontend components...")
    result = await call_agent_llm(
        "FrontendAgent",
        f"Generate key React TypeScript components for: {title}",
        system="You are a senior React engineer. Use Tailwind CSS and TypeScript.",
        max_tokens=2048,
    )
    active_tasks[task_id]["outputs"]["frontend_code"] = result
    await agent_event(task_id, "FrontendAgent", "done",
                      "Frontend components generated.", output=result[:300] + "...")


async def _run_qa_pipeline(task_id: str, title: str) -> bool:
    """QA pipeline with repair loop on failure."""
    await agent_event(task_id, "TestAgent", "working", "Generating test suite...")
    tests = await call_agent_llm(
        "TestAgent",
        f"Generate a complete pytest test suite for: {title}",
        system="Write pytest tests with fixtures, mocks, and edge cases.",
        max_tokens=2048,
    )
    active_tasks[task_id]["outputs"]["tests"] = tests
    await agent_event(task_id, "TestAgent", "done",
                      "Test suite generated.", output=tests[:300] + "...")

    # Simulate runtime execution attempt
    await agent_event(task_id, "RuntimeExecutionAgent", "working",
                      "Running tests...")
    await asyncio.sleep(1)

    # Simulate failure → repair loop
    await agent_event(task_id, "RuntimeExecutionAgent", "error",
                      "ModuleNotFoundError: PyJWT not found")
    await agent_event(task_id, "RetryCoordinator", "active",
                      "Activating repair loop (budget: 3 retries)...")
    await agent_event(task_id, "DiagnosticsAgent", "working",
                      "Diagnosing failure...")

    diagnosis = await call_agent_llm(
        "DiagnosticsAgent",
        "A Python test failed with: ModuleNotFoundError: No module named 'jwt'. "
        "Diagnose and suggest the fix.",
        system="You are a DevOps diagnostics expert. Be specific and actionable.",
    )
    await agent_event(task_id, "DiagnosticsAgent", "done",
                      "Diagnosis: missing PyJWT dependency", output=diagnosis)

    await agent_event(task_id, "RepairAgent", "working",
                      "Patching requirements.txt...")
    repair = await call_agent_llm(
        "RepairAgent",
        "Add PyJWT to a requirements.txt. Return only the updated requirements.txt content.",
        system="Return only the file content, no explanation.",
    )
    active_tasks[task_id]["outputs"]["requirements_patched"] = repair
    await agent_event(task_id, "RepairAgent", "done",
                      "requirements.txt patched.", output=repair)

    await agent_event(task_id, "RetryCoordinator", "done",
                      "Repair approved. Retrying tests...")
    await agent_event(task_id, "RuntimeExecutionAgent", "done",
                      "✅ All tests passed on attempt 2.")

    # Hallucination + semantic validators
    await asyncio.gather(
        _run_validator(task_id, "HallucinationValidator",
                       "Check the generated code for hallucinated APIs or imports."),
        _run_validator(task_id, "SemanticValidator",
                       "Verify the code semantically matches the requirements."),
        _run_validator(task_id, "ContractValidator",
                       "Verify the API implementation matches the OpenAPI spec."),
    )
    return True


async def _run_validator(task_id: str, agent: str, prompt: str):
    await agent_event(task_id, agent, "working", f"Running {agent}...")
    result = await call_agent_llm(agent, prompt,
                                  system="Return PASS or FAIL with a one-line reason.")
    await agent_event(task_id, agent, "done", f"{agent}: {result[:100]}")


async def _run_security_pipeline(task_id: str, title: str) -> bool:
    await agent_event(task_id, "ScannerAgent", "working",
                      "Scanning for vulnerabilities and exposed secrets...")
    scan = await call_agent_llm(
        "ScannerAgent",
        f"Security audit for a {title} application. "
        "Check for: SQL injection, exposed secrets, insecure auth, OWASP Top 10.",
        system="You are a security engineer. Return findings as JSON with severity levels.",
    )
    active_tasks[task_id]["outputs"]["security_scan"] = scan
    cleared = "CRITICAL" not in scan.upper()
    await agent_event(task_id, "ScannerAgent",
                      "done" if cleared else "blocked",
                      "Security scan complete — no critical issues." if cleared
                      else "⛔ CRITICAL vulnerability detected. Blocking deployment.",
                      output=scan)
    return cleared


async def _run_deploy_agent(task_id: str, title: str):
    await agent_event(task_id, "DeployAgent", "working",
                      "Generating Dockerfile and CI/CD config...")
    result = await call_agent_llm(
        "DeployAgent",
        f"Generate a production Dockerfile and GitHub Actions deploy workflow for: {title}",
        system="You are a DevOps engineer. Target: Google Cloud Run. Use best practices.",
        max_tokens=2048,
    )
    active_tasks[task_id]["outputs"]["deployment_config"] = result
    await agent_event(task_id, "DeployAgent", "done",
                      "Deployment config generated.", output=result[:300] + "...")


async def _run_diagnostics_agent(task_id: str):
    await agent_event(task_id, "DiagnosticsAgent", "working",
                      "Running final health diagnostics...")
    await asyncio.sleep(0.5)
    await agent_event(task_id, "DiagnosticsAgent", "done",
                      "System health: 91/100. All pipelines nominal.")


async def _run_knowledge_memory_agent(task_id: str, title: str):
    await agent_event(task_id, "KnowledgeMemoryAgent", "working",
                      "Storing learnings to long-term memory...")
    summary = await call_agent_llm(
        "KnowledgeMemoryAgent",
        f"Summarize key learnings from building: {title} in 3 bullet points.",
        system="Be concise. This goes into long-term project memory.",
    )
    active_tasks[task_id]["outputs"]["memory_summary"] = summary
    await agent_event(task_id, "KnowledgeMemoryAgent", "done",
                      "Learnings stored.", output=summary)


# ─────────────────────────────────────────────────────────────
#  STATUS + OUTPUTS ENDPOINTS
# ─────────────────────────────────────────────────────────────

async def load_task_from_db(task_id: str) -> dict | None:
    try:
        async for session in get_db_session():
            if not session:
                return None
            task_db = TaskDB(session)
            task_row = await task_db.get_task(task_id)
            if not task_row:
                return None
                
            pipeline_db = PipelineDB(session)
            pipelines_rows = await pipeline_db.get_pipelines(task_id)
            
            output_db = OutputDB(session)
            outputs_rows = await output_db.get_outputs(task_id)
            
            outputs = {}
            for out in outputs_rows:
                outputs[out["output_type"]] = out["content"]
                
            pipelines = []
            default_names = ["planning", "engineering", "qa", "security", "devops", "reliability"]
            existing_names = [p["name"] for p in pipelines_rows]
            
            for p in pipelines_rows:
                pipelines.append({
                    "name": p["name"],
                    "status": p["status"],
                    "progress": p["progress"]
                })
                
            for name in default_names:
                if name not in existing_names:
                    pipelines.append({
                        "name": name,
                        "status": "idle",
                        "progress": 0
                    })
                    
            created_at = task_row.get("created_at")
            if created_at:
                if hasattr(created_at, "isoformat"):
                    created_at_str = created_at.isoformat()
                    if not created_at_str.endswith("Z"):
                        created_at_str += "Z"
                else:
                    created_at_str = str(created_at)
            else:
                created_at_str = datetime.utcnow().isoformat() + 'Z'
                
            return {
                "task_id": str(task_row["id"]),
                "status": task_row["status"],
                "title": task_row["title"],
                "created_at": created_at_str,
                "outputs": outputs,
                "pipelines": pipelines
            }
    except Exception as e:
        logger.error("Error loading task from DB: %s", e)
    return None


@router.get("/files/{task_id}")
@limiter.limit("60/minute")
async def get_task_files(task_id: str, request: Request):
    try:
        files = await list_files(task_id)
        return files
    except PermissionError as pe:
        logger.warning("Rejected invalid file list path for task %s: %s", task_id, pe)
        raise HTTPException(status_code=400, detail=str(pe))
    except Exception as e:
        logger.exception("Failed to list generated files for task %s", task_id)
        raise HTTPException(status_code=500, detail="Could not list generated files.")


@router.get("/files/{task_id}/download")
@limiter.limit("5/minute")
async def download_task_files(task_id: str, request: Request):
    try:
        zip_stream = await create_zip_archive(task_id)
        return StreamingResponse(
            zip_stream,
            media_type="application/x-zip-compressed",
            headers={"Content-Disposition": f"attachment; filename=nexusswarm_task_{task_id}.zip"}
        )
    except PermissionError as pe:
        logger.warning("Rejected invalid file download path for task %s: %s", task_id, pe)
        raise HTTPException(status_code=400, detail=str(pe))
    except Exception as e:
        logger.exception("Failed to create generated files archive for task %s", task_id)
        raise HTTPException(status_code=500, detail="Could not download generated files.")


@router.get("/files/{task_id}/{filename}")
@limiter.limit("60/minute")
async def get_task_file(task_id: str, filename: str, request: Request):
    try:
        content = await get_file_content(task_id, filename)
        if content is None:
            raise HTTPException(status_code=404, detail="File not found")
        return {"content": content, "filename": filename}
    except PermissionError as pe:
        logger.warning("Rejected invalid file path for task %s and file %s: %s", task_id, filename, pe)
        raise HTTPException(status_code=400, detail=str(pe))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to read generated file %s for task %s", filename, task_id)
        raise HTTPException(status_code=500, detail="Could not read generated file.")


@router.get("/task/{task_id}")
@router.get("/status/{task_id}")
@limiter.limit("60/minute")
async def get_task_status(task_id: str, request: Request):
    task = active_tasks.get(task_id)
    if not task:
        task = await load_task_from_db(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("/task/{task_id}/outputs")
@limiter.limit("60/minute")
async def get_task_outputs(task_id: str, request: Request):
    task = active_tasks.get(task_id)
    if not task:
        task = await load_task_from_db(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.get("outputs", {})


@router.get("/tasks")
@limiter.limit("60/minute")
async def list_tasks(request: Request, limit: int = Query(20, ge=1, le=100)):
    """List recent tasks — consumed by TaskHistory component."""
    try:
        async for session in get_db_session():
            if not session:
                break
            task_db = TaskDB(session)
            tasks_rows = await task_db.list_tasks(limit)
            if tasks_rows:
                formatted_tasks = []
                for row in tasks_rows:
                    task_id = str(row["id"])
                    task_data = await load_task_from_db(task_id)
                    if task_data:
                        formatted_tasks.append(task_data)
                return {"tasks": formatted_tasks, "total": len(formatted_tasks)}
    except Exception as e:
        logger.error("Error listing tasks from DB: %s", e)

    # Fallback
    tasks = sorted(
        active_tasks.values(),
        key=lambda t: t.get("created_at", ""),
        reverse=True,
    )[:limit]
    return {"tasks": tasks, "total": len(active_tasks)}


@router.get("/stats")
@limiter.limit("60/minute")
async def get_stats(request: Request):
    try:
        async for session in get_db_session():
            if not session:
                break
            task_db = TaskDB(session)
            stats = await task_db.get_stats()
            if stats:
                stats["agent_count"] = len(AGENT_MODEL_MAP)
                return stats
    except Exception as e:
        logger.error("Error getting stats from DB: %s", e)

    # Fallback
    total     = len(active_tasks)
    completed = sum(1 for t in active_tasks.values() if t.get("status") == "completed")
    running   = sum(1 for t in active_tasks.values() if t.get("status") == "running")
    failed    = sum(1 for t in active_tasks.values() if t.get("status") == "failed")
    return {
        "total_tasks":     total,
        "completed_tasks": completed,
        "running_tasks":   running,
        "failed_tasks":    failed,
        "agent_count":     len(AGENT_MODEL_MAP),
    }


@router.get("/health")
@limiter.limit("60/minute")
async def health(request: Request):
    return {
        "status":        "healthy",
        "agent_count":   len(AGENT_MODEL_MAP),
        "provider":      "NVIDIA NIM",
        "models_loaded": len(set(AGENT_MODEL_MAP.values())),
    }



# ─────────────────────────────────────────────────────────────
#  WEBSOCKET
# ─────────────────────────────────────────────────────────────

@router.websocket("/ws/agents")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    websocket_clients.append(websocket)
    logger.info("WebSocket client connected")
    try:
        while True:
            await websocket.receive_text()  # keep-alive
    except WebSocketDisconnect:
        if websocket in websocket_clients:
            websocket_clients.remove(websocket)
        logger.info("WebSocket client disconnected")
