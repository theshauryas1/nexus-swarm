# ⬡ NexusSwarm — Technical Requirements Document (TRD)

## 1. System Topology & Architectural Layers

NexusSwarm's technical topology is structured as a robust, microservices-oriented web application consisting of a React SPA frontend, a Python FastAPI backend, a PostgreSQL relational store, and Google Cloud Storage buckets.

```
┌────────────────────────────────────────────────────────┐
│                      FRONTEND SPA                      │
│      React 18 / Zustand Store / Tailwind CSS v4        │
│       React Flow Canvas / Monaco Code Editor           │
└──────────────────────────┬─────────────────────────────┘
                           │ (HTTP REST / WebSockets)
                           ▼
┌────────────────────────────────────────────────────────┐
│                     BACKEND ENGINE                     │
│      FastAPI / Asyncio Pipelines / autogen Core        │
│         NVIDIA NIM OpenAI-Compatible API Client        │
└──────────┬───────────────────┬───────────────────┬─────┘
           │                   │                   │
           ▼                   ▼                   ▼
┌────────────────────┐ ┌──────────────┐ ┌────────────────┐
│ DATABASE CLUSTER   │ │ BLOB STORAGE │ │ CLOUD SHELL    │
│ PostgreSQL / SQL   │ │ GCS Bucket / │ │ Google Cloud   │
│ Alchemy AsyncPG    │ │ Local Disk   │ │ Shell Console  │
└────────────────────┘ └──────────────┘ └────────────────┘
```

---

## 2. Component Specifications

### 2.1. Frontend Architecture
* **Framework**: React 18 with TypeScript 5, bundled using Vite.
* **State Management**: Zustand v4, maintaining a global reactive store (`useNexusStore`) for events, roster, statuses, file caches, and dynamic task sessions.
* **Visual Graph Engine**: `@xyflow/react` (React Flow) rendering custom manager, executive, and worker nodes.
* **Code Editor**: `@monaco-editor/react` with lazy-loaded language colorizers and custom styling themes.
* **Build Configuration**: Compiled using TypeScript compiler (`tsc`) and Vite builder into highly optimized chunked assets.

### 2.2. Backend Swarm Engine
* **Framework**: FastAPI (Python 3.11+) with Uvicorn server hosting.
* **Agent Framework**: Microsoft `autogen` SDK (v0.4.9) orchestrating hierarchical conversation threads.
* **Concurrency**: Python `asyncio` managing long-running background tasks, WebSocket event broadcasting, and file upload threads simultaneously.
* **Testing Sandbox**: Dedicated execution subsystem executing `pytest` in sandboxed Python sub-processes, capturing stdout/stderr and routing results back to the `DiagnosticsAgent`.

---

## 3. Database Schema & Memory Modeling
NexusSwarm utilizes PostgreSQL 15 for status tracking, system metrics, and audit logs. The engine integrates with SQLAlchemy (asyncpg) to provide non-blocking CRUD operations.

### 3.1. Entity Relationship & Table Schemas

#### 1. Table: `tasks`
Persistent records of submitted prompts and overall swarm state:
```sql
CREATE TABLE tasks (
    task_id VARCHAR(36) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'pending', -- pending, running, complete, failed
    priority INT DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb -- Stores parent_task_id, model configurations, etc.
);
CREATE INDEX idx_tasks_status ON tasks(status);
```

#### 2. Table: `pipelines`
Progress tracking for the 6 core software delivery pipelines:
```sql
CREATE TABLE pipelines (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(36) REFERENCES tasks(task_id) ON DELETE CASCADE,
    name VARCHAR(50) NOT NULL, -- planning, engineering, qa, security, devops, reliability
    status VARCHAR(50) DEFAULT 'idle', -- idle, active, blocked, done, failed
    progress INT DEFAULT 0,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX idx_task_pipeline ON pipelines(task_id, name);
```

#### 3. Table: `agent_logs`
High-volume write-only immutable stream for full audit records:
```sql
CREATE TABLE agent_logs (
    log_id SERIAL PRIMARY KEY,
    task_id VARCHAR(36) REFERENCES tasks(task_id) ON DELETE CASCADE,
    agent_name VARCHAR(100) NOT NULL,
    agent_level VARCHAR(50) NOT NULL, -- orchestrator, manager, worker, gateway
    pipeline_name VARCHAR(50),
    status VARCHAR(50) NOT NULL, -- idle, active, done, error, blocked
    message TEXT NOT NULL,
    payload JSONB DEFAULT '{}'::jsonb, -- Stores token usage, full prompt/response string
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_agent_logs_task ON agent_logs(task_id);
```

#### 4. Table: `task_outputs`
Stores the finalized code and markdown files associated with each task session:
```sql
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

## 4. API & Real-time WebSocket Protocol

### 4.1. HTTP REST Specifications

#### 1. Submit Swarm Task
* **Endpoint**: `POST /submit-task`
* **Request Payload**:
  ```json
  {
    "title": "Build FastAPI JWT Service",
    "description": "Create clean database authentication endpoints",
    "priority": 1,
    "parent_task_id": "optional-uuid-here"
  }
  ```
* **Success Response (200 OK)**:
  ```json
  {
    "status": "success",
    "task_id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
    "message": "Swarm pipeline started."
  }
  ```

#### 2. Fetch Multi-Session Files
* **Endpoint**: `GET /files/{task_id}`
* **Success Response (200 OK)**:
  ```json
  [
    { "name": "requirements.md", "size": 1024, "lang": "markdown" },
    { "name": "backend.py", "size": 4096, "lang": "python" },
    { "name": "test_backend.py", "size": 2048, "lang": "python" }
  ]
  ```

### 4.2. WebSocket Protocol (`ws://{api_url}/ws/agents`)
Maintains a single bidirectional channel pushing real-time events. Upon container launch, client subscribes to receive state frames:
```json
{
  "event_id": "evt-uuid-here",
  "event_type": "agent_update", -- agent_update, pipeline_update, complete
  "task_id": "task-uuid-here",
  "agent_name": "BackendAgent",
  "agent_level": "worker",
  "pipeline": "engineering",
  "status": "in_progress",
  "message": "Drafting async SQLAlchemy session helper...",
  "timestamp": "2026-05-31T11:24:54.000Z",
  "payload": {
    "tokens": 420,
    "model": "meta/llama-3.3-70b-instruct"
  }
}
```

---

## 5. Security & Prototype Pollution Protection

### 5.1. Dynamic Lookup Guard (`safeGet`)
Standard bracket notation in JavaScript (`obj[key]`) represents a security hazard if `key` is dynamic or user-controlled. It opens avenues for prototype pollution and arbitrary code execution.
NexusSwarm mandates the use of a secure lookup utility in all components:

```typescript
export function safeGet<T extends object, K extends string>(obj: T, key: K): any {
  if (!obj || !key || key === '__proto__' || key === 'constructor' || key === 'prototype') {
    return undefined;
  }
  return Object.prototype.hasOwnProperty.call(obj, key) ? (obj as any)[key] : undefined;
}
```
This utility explicitly validates the property key against unsafe prototype variables and performs safe checks using `Object.prototype.hasOwnProperty`.

---

## 6. Cloud Native Infrastructure Specifications

NexusSwarm's automated build and continuous delivery pipeline is implemented inside Google Cloud Build using Google Secret Manager and Google Cloud Run.

### 6.1. Google Cloud Run Deployment Env Variables
* `APP_ENV`: `production`
* `DATABASE_URL`: `postgresql+asyncpg://postgres:$$DB_PASSWORD@/nexusswarm?host=/cloudsql/{_DB_CONNECTION}`
* `GCS_BUCKET`: `nexusswarm-outputs-{project_id}`
* `NVIDIA_API_KEY`: Mounted via Secret Manager mapping.

### 6.2. PowerShell Command Line Compilation Warning
In standard Windows PowerShell environments, argument comma lists like `--substitutions=_DB_CONNECTION="...",_GCS_BUCKET="..."` get implicitly merged as an array joined with space, causing compilation variables to corrupt.
Always wrap command substitution arrays in a single enclosed quote:
```powershell
gcloud builds submit --config=deploy/cloudbuild.yaml `
  "--substitutions=_DB_CONNECTION=nexusswarm-54c977:us-central1:nexusswarm-db,_GCS_BUCKET=nexusswarm-outputs-nexusswarm-54c977"
```
This preserves the exact comma-separated format across CMD and PowerShell boundaries.
