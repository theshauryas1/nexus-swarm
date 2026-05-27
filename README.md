# ⬡ NexusSwarm

> **Hierarchical Multi-Agent Governance** — A Microsoft AI Hackathon submission (Theme 05)
>
> An AI organizational hierarchy that mirrors real enterprise structure:  
> Executive Orchestrator → Pipeline Managers → Specialist Workers  
> _Governance isn't just in the prompts — it's enforced at the tool layer._

---

## Architecture

```
HEAD ORCHESTRATOR (Level 1 — Executive)
    ├── PlanningManager
    │   ├── RequirementAgent   → extracts spec, writes requirements.md
    │   └── RiskAnalyzer       → risk register, go/no-go assessment
    │
    ├── EngineeringManager
    │   ├── BackendAgent       → writes complete FastAPI application
    │   └── APIAgent           → writes router files, OpenAPI contracts
    │
    ├── QAManager
    │   └── TestAgent          → pytest test suite, fixtures, mocks
    │
    ├── SecurityManager  ←── CAN BLOCK DevOps
    │   └── ScannerAgent       → secrets scan + vulnerability analysis
    │
    └── DevOpsManager    ←── WAITS for Security clearance
        └── DeployAgent        → Dockerfile, docker-compose, GitHub Actions
```

**Custom MCP Servers** (governance enforced at tool layer):
| Server | Tools | Used by |
|--------|-------|---------|
| `logger_mcp`          | `log_agent_action`, `broadcast_event` | All agents |
| `security_mcp`        | `scan_for_secrets`, `check_unsafe_patterns`, `scan_file` | ScannerAgent |
| `quality_mcp`         | `lint_python`, `check_complexity`, `estimate_test_coverage` | TestAgent, QAManager |
| `pipeline_status_mcp` | `get_pipeline_health`, `update_pipeline_progress` | HeadOrchestrator |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **LLM** | NVIDIA NIM (`llama-3.1-70b-instruct`) / Azure OpenAI fallback |
| **Agent Framework** | Microsoft AutoGen v0.4 (`autogen-agentchat`, `autogen-ext`) |
| **MCP** | Model Context Protocol (custom stdio MCP servers) |
| **Backend** | FastAPI, SQLAlchemy 2.0 async, asyncpg |
| **State** | Redis (pub/sub + pipeline state), PostgreSQL (audit trail) |
| **Frontend** | React 18, Vite, Tailwind CSS, React Flow, Zustand |
| **Live Events** | WebSocket → Redis pub/sub → React store → UI |
| **Deploy** | Docker Compose (local), Azure Container Apps (production) |
| **CI/CD** | GitHub Actions (test → build → push → deploy) |

---

## Quick Start (Local)

### Prerequisites
- Docker Desktop
- NVIDIA NIM API key (free tier at [build.nvidia.com](https://build.nvidia.com))
- OR Azure OpenAI endpoint + key

### 1. Clone & configure

```bash
git clone https://github.com/YOUR_ORG/nexusswarm
cd nexusswarm
cp .env.example .env
```

Edit `.env`:
```env
NVIDIA_API_KEY=
# OR
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_DEPLOYMENT_ORCHESTRATOR=
```

### 2. Launch the swarm

```bash
docker compose up --build
```

Services:
| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Health | http://localhost:8000/health |

### 3. Submit a task

Click **"Load Demo"** in the UI and hit **"Launch Swarm"**.

Or via API:
```bash
curl -X POST http://localhost:8000/submit-task \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Build a secure REST API for task management",
    "description": "Include JWT auth, CRUD, PostgreSQL, pytest tests, Docker"
  }'
```

Watch the React Flow graph come alive as 15 agents coordinate in real time.

---

## API Reference

```
POST  /submit-task          Submit a new task to the swarm
GET   /task/{task_id}       Get task status
GET   /task/{task_id}/outputs  Get all generated outputs
GET   /agents               Get agent roster with live statuses
GET   /pipelines/{task_id}  Get pipeline health for a task
GET   /health               Health check (DB + Redis connectivity)
WS    /ws/agents            Live event stream (WebSocket)
```

---

## Azure Deployment

### One-time setup

```bash
# Install Azure CLI
az login

# Set your NVIDIA and OpenAI keys in .env or your deployment secret manager.

# Run provisioning script
bash deploy/azure_provision.sh
```

### GitHub Secrets required

| Secret | Description |
|--------|-------------|
| `AZURE_CREDENTIALS` | Service principal JSON (`az ad sp create-for-rbac`) |
| `NVIDIA_API_KEY` | NVIDIA NIM API key |
| `AZURE_OPENAI_KEY` | Azure OpenAI API key |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL |

After setup, every push to `main` triggers: **Test → Build → Push → Deploy**.

---

## How Governance Works

**Without managers:** Agents are chaotic — token usage explodes, tasks duplicate, context fragments.

**With NexusSwarm's hierarchy:**

1. **SecurityManager** can literally **BLOCK** DevOpsManager from deploying if critical vulnerabilities are found
2. **QAManager** enforces a quality gate before handing off to Security
3. **HeadOrchestrator** resolves conflicts and decides whether to escalate or proceed conditionally
4. **MCP servers** enforce role boundaries — Security agents only get security tools, QA agents only get quality tools
5. Every agent action is **logged to PostgreSQL** and **broadcast to the frontend** in real time

This is AI governance as infrastructure, not just as prompts.

---

## Project Structure

```
nexusswarm/
├── backend/
│   ├── agents/
│   │   ├── orchestrator.py        # Head Orchestrator (Level 1)
│   │   ├── runner.py              # FastAPI → orchestrator bridge
│   │   ├── base.py                # EventEmitter, AgentContext
│   │   ├── llm_factory.py         # NVIDIA NIM / Azure routing
│   │   ├── managers/              # 5 pipeline managers (Level 2)
│   │   └── workers/               # 7 specialist workers (Level 3)
│   ├── mcp_servers/               # 4 custom MCP servers
│   ├── memory/                    # Redis + PostgreSQL clients
│   ├── db/init.sql                # Schema: tasks, pipelines, logs, outputs
│   ├── main.py                    # FastAPI app
│   └── routes.py                  # All API + WebSocket routes
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── AgentGraph.tsx     # React Flow hierarchy (live)
│       │   ├── TaskDashboard.tsx  # Submit + pipeline health bars
│       │   ├── LiveLog.tsx        # Real-time event feed
│       │   └── OutputPanel.tsx    # Roster, output, stats
│       ├── hooks/useAgentStream.ts # WebSocket auto-reconnect
│       └── store/agentStore.ts    # Zustand global state
├── .github/workflows/deploy.yml   # CI/CD pipeline
├── deploy/azure_provision.sh      # Azure infrastructure setup
└── docker-compose.yml             # Local full-stack launch
```

---

## Hackathon Theme

**Theme 05 — AI Agents & Automation**

NexusSwarm demonstrates:
- ✅ **Hierarchical Multi-Agent Governance** (not peer-to-peer chaos)
- ✅ **Real MCP integration** (4 custom stdio MCP servers)
- ✅ **NVIDIA NIM** as primary LLM provider
- ✅ **Microsoft Azure Container Apps** as deployment target
- ✅ **Real-time observability** (WebSocket → Redis pub/sub → React Flow)
- ✅ **Security as a pipeline gate** (not an afterthought)
- ✅ **Enterprise-grade audit trail** (PostgreSQL log of every agent action)

---

## License

MIT
