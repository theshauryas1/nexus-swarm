# ⬡ NexusSwarm v2

> **Hierarchical Multi-Agent Governance & AI Engineering Operating System**  
> *An AI organizational hierarchy mirroring real enterprise engineering divisions where quality, security, and integration rules are enforced at the tool layer.*

**NexusSwarm** is a 28-agent multi-agent platform built on Microsoft AutoGen, FastAPI, React, and NVIDIA NIM. It implements an executive, manager, and worker hierarchy automating software and AI engineering from requirements through deployment. A dynamic model router cut average task time by 62% on NIM's free tier by routing tasks to right-sized models instead of one large model. Includes guardrails against prompt injection, secret leakage, and hallucinated imports. Evaluated with a 100-task, 9-category benchmark suite and a resilience test report where 4 of 5 attack tests were blocked.

---

## ⚡ Key Highlights & Benchmark Results

- **28-Agent Hierarchical Governance**: Executive, Manager, and Worker tiers divide concerns across Planning, Engineering, QA, Security, Reliability, and DevOps pipelines.
- **62% Latency Reduction**: A dynamic model router cut average task execution time by **62%** on NVIDIA NIM's free tier by routing tasks to right-sized models (e.g. `nemotron-3-super-120b`, `llama-3.2-11b-vision`, `nemotron-3-nano-30b`) instead of routing all agent steps to one large model.
- **Enterprise Guardrails**: Enforces runtime protection against prompt injection, secret leakage, and AST-validated hallucinated package imports.
- **100-Task Benchmark Suite**: Evaluated across 9 categorized domains (Adversarial, Hallucination, Security, Self-Repair, Auth, Backend, Docker, Deployment, WebSocket) with multi-signal objective verification.
- **Resilience Test Suite**: In live adversarial resilience testing, **4 of 5 attack tests were blocked** (blocking prompt injections, fake package hallucination traps, CVE/RCE exploits, and secret exfiltration).

---

## 📊 Evaluation & Resilience Metrics

| Metric / Dimension | Specification & Results | Details & Evidence |
| :--- | :--- | :--- |
| **Benchmark Suite** | **100 Tasks / 9 Categories** | Covers `adversarial` (7), `hallucination` (12), `security` (12), `repair` (13), `auth` (12), `backend` (15), `docker` (12), `deployment` (12), and `websocket` (12) |
| **Latency Reduction** | **62% Average Task Time Cut** | Model router dynamically selects right-sized NIM models per agent role instead of one large model (45s+ down to sub-15s pipelines) |
| **Adversarial Resilience** | **4 / 5 Attacks Blocked (80%)** | Prompt injection (`T03`), hallucination trap (`T02`), RCE/eval patterns (`T05`), and CVE fake-package combo (`T10`) caught and blocked |
| **Import Hallucination Defense** | **AST Validation** | Statically parses generated code to detect and reject non-existent packages (e.g., `superauth-enterprise-pro`, `pyjwt-enterprise`) |
| **Self-Correction & Repair** | **Automated QA Loop** | Pytest tracebacks triaged by QAManager, patched by CoderAgent, and verified autonomously up to 3 retry iterations |
| **Token Budget & Cost Tracking** | **LLMOps Telemetry** | Real-time token usage and cost accounting per task via `cost_tracker.py` |

---

## 📖 Documentation Directory

The project contains complete documentation covering system design, API contracts, database layers, and developer onboarding:

- **[CONTEXT.md](CONTEXT.md)**: Product specifications, target user personas, and core component workflows.
- **[architecture.md](architecture.md)**: System topology, agent hierarchy (Executive → Manager → Worker), and custom Model Context Protocol (MCP) server definitions.
- **[api.md](api.md)**: FastAPI REST endpoints, Pydantic schemas, WebSocket logs protocol, and rate-limiting guardrails.
- **[database.md](database.md)**: PostgreSQL production and SQLite local database schemas, entity-relationship diagrams (ERD), and tables structures.
- **[onboarding.md](onboarding.md)**: Local machine installation steps, Docker Compose guides, test suite executions, and developer scripts.
- **[deploy/README.md](deploy/README.md)** & **[docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md)**: Complete Google Cloud deployment architecture, Cloud Run setup, and Cloud Build CI/CD.
- **[learning_notes.md](learning_notes.md)** *(Excluded from git tracking)*: Practical lessons on AutoGen state synchronization, prototype pollution prevention, and NIM routing optimizations.
- **[interview_notes.md](interview_notes.md)** *(Excluded from git tracking)*: Structural design review notes, engineering tradeoffs, and conceptual Q&As.

---

## 🌐 Live Google Cloud Deployment

The application is deployed live on Google Cloud Platform (Cloud Run, Cloud SQL, Artifact Registry, Secret Manager, Cloud Build):

- 🖥️ **Frontend IDE Dashboard**: [https://nexusswarm-frontend-669943047856.us-central1.run.app](https://nexusswarm-frontend-669943047856.us-central1.run.app)
- ⚙️ **Backend REST & WebSocket API**: [https://nexusswarm-backend-669943047856.us-central1.run.app](https://nexusswarm-backend-669943047856.us-central1.run.app)
- 📚 **Interactive Swagger API Docs**: [https://nexusswarm-backend-669943047856.us-central1.run.app/docs](https://nexusswarm-backend-669943047856.us-central1.run.app/docs)

---

## 🛠️ Technology Stack

| Layer | Technology |
| :--- | :--- |
| **Cloud Hosting** | Google Cloud Run (Fully Managed, Auto-scaling Serverless Containers, Unthrottled CPU) |
| **Cloud Infrastructure** | Google Cloud SQL (PostgreSQL), Artifact Registry, Cloud Build, Secret Manager, GCS |
| **Agent Framework** | Microsoft AutoGen v0.4 (`autogen-agentchat`, `autogen-ext`) |
| **Model Router** | Intelligent Model Router with Dynamic Fallback Chains per agent & task |
| **Primary LLMs** | • **NVIDIA NIM**: `nemotron-3-super-120b`, `llama-3.2-11b-vision`, `nemotron-3-nano-30b`, `nemotron-3.5-lightning`<br>• **Google Gemini**: `gemini-2.0-flash`, `gemini-1.5-pro` (Zero-latency cloud failover) |
| **Embedding Engine** | `nvidia/llama-nemotron-embed-vl-1b-v2` & Deterministic Normalized Vectorizer |
| **Tool Interface** | Model Context Protocol (stdio servers: `logger_mcp`, `security_mcp`, `quality_mcp`, `pipeline_status_mcp`) |
| **Backend** | FastAPI, SQLAlchemy 2.0 (Async), Pydantic v2 |
| **Relational Storage** | PostgreSQL 15 (Cloud SQL) / Local SQLite fallback |
| **Semantic Memory** | PostgreSQL `pgvector` with 1024-dimension vector embeddings |
| **Frontend UI** | React 18, Vite, Tailwind CSS, Zustand v4, React Flow, Monaco Editor |

---

## 🚀 Quick Start (Local & Cloud)

### 1. Clone & Configure
```bash
git clone https://github.com/theshauryas1/nexus-swarm.git
cd nexus-swarm
cp .env.example .env
```

Edit your `.env` to supply your `NVIDIA_API_KEY` (free key from [build.nvidia.com](https://build.nvidia.com)) or `GEMINI_API_KEY`.

### 2. Launch Services Locally
```bash
docker compose up --build
```

- **Dashboard**: `http://localhost:3000`
- **Backend API**: `http://localhost:8000`
- **API Swagger Docs**: `http://localhost:8000/docs`

### 3. Deploy to Google Cloud Run
```bash
# Provision Cloud Infrastructure (one-time)
./deploy/setup.sh

# Deploy entire stack (Backend + Frontend)
gcloud builds submit --config=deploy/cloudbuild.yaml

# Deploy Backend only
gcloud builds submit --config=deploy/cloudbuild-backend.yaml

# Deploy Frontend only
gcloud builds submit --config=deploy/cloudbuild-frontend.yaml
```
