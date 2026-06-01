# ⬡ NexusSwarm — Backend Schema & Implementation Plan

## 1. Relational Database Schema (PostgreSQL)

NexusSwarm utilizes a PostgreSQL 15 relational store. The database schema tracks prompt lifecycle, pipeline state transitions, agent execution histories, and generated outputs.

```
                  ┌──────────────────────┐
                  │        tasks         │
                  ├──────────────────────┤
                  │ PK   task_id         │◄──────────┐
                  │      title           │           │
                  │      description     │           │
                  │      status          │           │
                  │      priority        │           │
                  │      created_at      │           │
                  │      metadata        │           │
                  └──────────┬───────────┘           │
                             │                       │
           ┌─────────────────┼─────────────────┐     │
           │ 1:Many          │ 1:Many          │     │ 1:Many
           ▼                 ▼                 ▼     │
┌──────────────────────┐ ┌──────────────┐ ┌──────────┴───────────┐
│      pipelines       │ │  agent_logs  │ │     task_outputs     │
│──────────────────────│ ├──────────────┤ ├──────────────────────┤
│ PK   id              │ │ PK   log_id  │ │ PK   output_id       │
│ FK   task_id         │ │ FK   task_id │ │ FK   task_id         │
│      name            │ │      agent   │ │      agent_name      │
│      status          │ │      level   │ │      output_type     │
│      progress        │ │      pipeline│ │      content         │
│      updated_at      │ │      status  │ │      created_at      │
│                      │ │      message │ └──────────────────────┘
│                      │ │      payload │
│                      │ │      created │
└──────────────────────┘ └──────────────┘
```

### 1.1. Data Definition Queries

```sql
-- ── 1. Tasks Table ──
CREATE TABLE tasks (
    task_id VARCHAR(36) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'pending', -- pending, running, complete, failed
    priority INT DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb -- parent_task_id, model configuration details
);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_created_at ON tasks(created_at DESC);

-- ── 2. Pipelines Table ──
CREATE TABLE pipelines (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(36) REFERENCES tasks(task_id) ON DELETE CASCADE,
    name VARCHAR(50) NOT NULL, -- planning, engineering, qa, security, devops, reliability
    status VARCHAR(50) DEFAULT 'idle', -- idle, active, blocked, done, failed
    progress INT DEFAULT 0,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX idx_task_pipeline ON pipelines(task_id, name);

-- ── 3. Agent Logs Table ──
CREATE TABLE agent_logs (
    log_id SERIAL PRIMARY KEY,
    task_id VARCHAR(36) REFERENCES tasks(task_id) ON DELETE CASCADE,
    agent_name VARCHAR(100) NOT NULL,
    agent_level VARCHAR(50) NOT NULL, -- orchestrator, manager, worker, gateway
    pipeline_name VARCHAR(50),
    status VARCHAR(50) NOT NULL, -- idle, active, done, error, blocked
    message TEXT NOT NULL,
    payload JSONB DEFAULT '{}'::jsonb, -- token use details, raw LLM prompt / response text
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_agent_logs_task ON agent_logs(task_id);
CREATE INDEX idx_agent_logs_created_at ON agent_logs(created_at DESC);

-- ── 4. Task Outputs Table ──
CREATE TABLE task_outputs (
    output_id SERIAL PRIMARY KEY,
    task_id VARCHAR(36) REFERENCES tasks(task_id) ON DELETE CASCADE,
    agent_name VARCHAR(100) NOT NULL,
    output_type VARCHAR(50) NOT NULL, -- BackendAgent, TestAgent, etc.
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX idx_task_output_agent ON task_outputs(task_id, agent_name);
```

---

## 2. API Contract Schemas (Pydantic / FastAPI)

```python
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# ── 2.1. Request Schemas ──
class TaskSubmitRequest(BaseModel):
    title: str = Field(..., max_length=255, description="Short summary of task")
    description: Optional[str] = Field(None, description="Detailed explanation of task specs")
    priority: Optional[int] = Field(1, ge=1, le=5, description="Task Priority (1-5)")
    parent_task_id: Optional[str] = Field(None, description="Reference ID for project history context")

# ── 2.2. Response Schemas ──
class TaskSubmitResponse(BaseModel):
    status: str = Field("success", description="Indicates status of task acceptance")
    task_id: str = Field(..., description="Universally Unique Identifier for task tracking")
    message: str = Field(..., description="Human-readable notification text")

class FileItem(BaseModel):
    name: str = Field(..., description="File Basename (e.g. backend.py)")
    size: int = Field(..., description="File size in bytes")
    lang: str = Field("plaintext", description="Language mapping hint for Monaco styling")

class TaskStatusResponse(BaseModel):
    task_id: str
    title: str
    description: Optional[str]
    status: str
    priority: int
    created_at: datetime
    pipelines: List[Dict[str, Any]]
    outputs: Dict[str, str]
    metadata: Dict[str, Any]
```

---

## 3. Storage Architecture: Local Workspace & GCS Bucket

To achieve high availability and container persistence across multiple Cloud Run replicas, NexusSwarm operates on a **dual-replica file system strategy**.

```
                           ┌─────────────────────────┐
                           │      Agent Writer       │
                           └────────────┬────────────┘
                                        │
                         ┌──────────────┴──────────────┐
                         ▼ Concurrently                ▼ Concurrently
              ┌─────────────────────┐       ┌──────────────────────┐
              │   Local Workspace   │       │ Google Cloud Storage │
              │ /app/workspace/{id} │       │   gs://{bucket}/{id} │
              └─────────────────────┘       └──────────────────────┘
```

### 3.2. Fallback Mechanism (Defensive Design)
If Google Cloud credentials are not detected or GCS throws socket timeouts during startup checks:
1. The engine prints a clear, non-fatal alert warning: `[WARNING] GCS bucket bucket-name not connected. Falling back to local disk storage.`
2. The storage client automatically reroutes write/read operations exclusively to local file workspace.
3. The health checker returns status `200 OK (with storage degradation metadata)`.

---

## 4. Phase-Gated Swarm Implementation Plan

### Phase 1: Database & GCS Infrastructure Setup
* **Objective**: Configure relational database cluster, create buckets, and define non-blocking connection clients.
* **Tasks**:
  1. Initialize asyncpg pool engine with SQLAlchemy transaction managers.
  2. Implement migrations (`alembic`) applying the database schemas to Cloud SQL.
  3. Formulate GCS bucket read/write interfaces with local workspace fallback wrappers.
  4. Write unit tests checking local disk fallback capabilities when GCS credentials are mock deleted.

### Phase 2: Hierarchical Conversation Pipelines
* **Objective**: Formulate the multi-agent hierarchy conversation pathways utilizing Autogen.
* **Tasks**:
  1. Build the executive `HeadOrchestrator` system prompts managing conversation paths.
  2. Implement optimized model mappings within `llm_factory.py` pointing to NVIDIA NIM Llama models.
  3. Program Manager agents (`PlanningManager`, `EngineeringManager`, `QAManager`, `SecurityManager`, `DevOpsManager`, `ReliabilityManager`) that manage specialist conversation boundaries.
  4. Write conversation triggers passing context memory strings when `parent_task_id` is supplied.

### Phase 3: QA Execution Sandbox & Diagnostics Loop
* **Objective**: Execute generated codes, catch exit codes, and execute autonomous repair loops.
* **Tasks**:
  1. Set up sandboxed subprocess pipelines inside backend containers using isolated context blocks.
  2. Write regex exception parsers that map Python tracebacks (e.g. `ModuleNotFoundError`) into diagnostic models.
  3. Create an automated `DiagnosticsAgent` + `RepairAgent` dialog loop that edits `requirements.txt` or syntax structures, runs the test command again, and repeats up to **5 iterations**.

### Phase 4: Static Scans & Security Approval Gates
* **Objective**: Audit dependencies and scanned files for vulnerabilities, blocking unsafe deployments.
* **Tasks**:
  1. Write `ScannerAgent` algorithms mapping regex checks for keys, passwords, and typical prototype pollution patterns.
  2. If scan checks find **CRITICAL** issues, write blocking flags `status = 'blocked'` to SQL tables and trigger frontend UI overlays.
  3. Simulate token signatures inside `HumanApprovalGateway` representing gateway validation checks.

### Phase 5: Live WebSockets Event Feed
* **Objective**: Broadcast intermediate agent conversational state to active frontend connections.
* **Tasks**:
  1. Build a persistent WebSocket endpoint `/ws/agents` inside FastAPI router.
  2. Program state dispatch listeners that hook into Autogen conversation flows and parse log states.
  3. Broadcast JSON messages containing progress percentages, agent status indicators, and logs immediately to active sockets.

### Phase 6: Cloud Build Automated Continuous Delivery
* **Objective**: Automate setup scripts, Dockerfile compilations, and zero-config service rollouts.
* **Tasks**:
  1. Write `setup.sh` shell script bootstrap provisioning resources on user projects.
  2. Construct robust multi-stage `Dockerfile` and `nginx.conf` compilation files.
  3. Setup `cloudbuild.yaml` steps managing database SQL connections and Secret Manager keys.
