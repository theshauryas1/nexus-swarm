# ⬡ NexusSwarm v2

> **Hierarchical Multi-Agent Governance & AI Engineering Operating System**  
> _An AI organizational hierarchy mirroring real enterprise engineering divisions where quality, security, and integration rules are enforced at the tool layer._

---

## 📖 Documentation Directory

The project contains complete documentation covering system design, API contracts, database layers, and developer onboarding:

- **[context.md](file:///c:/hack/context.md)**: Product specifications, target user personas, and core component workflows.
- **[architecture.md](file:///c:/hack/architecture.md)**: System topology, agent hierarchy (Executive → Manager → Worker), and custom Model Context Protocol (MCP) server definitions.
- **[api.md](file:///c:/hack/api.md)**: FastAPI REST endpoints, Pydantic schemas, WebSocket logs protocol, and rate-limiting guardrails.
- **[database.md](file:///c:/hack/database.md)**: PostgreSQL production and SQLite local database schemas, entity-relationship diagrams (ERD), and tables structures.
- **[onboarding.md](file:///c:/hack/onboarding.md)**: Local machine installation steps, Docker Compose guides, test suite executions, and developer scripts.
- **[deploy/README.md](file:///c:/hack/deploy/README.md)** & **[docs/DEPLOYMENT_GUIDE.md](file:///c:/hack/docs/DEPLOYMENT_GUIDE.md)**: Complete Google Cloud deployment architecture, Cloud Run setup, and Cloud Build CI/CD.
- **[learning_notes.md](file:///c:/hack/learning_notes.md)** *(Excluded from git tracking)*: Practical lessons on AutoGen state synchronization, prototype pollution prevention, and NIM routing optimizations.
- **[interview_notes.md](file:///c:/hack/interview_notes.md)** *(Excluded from git tracking)*: Structural design review notes, engineering tradeoffs, and conceptual Q&As.

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
