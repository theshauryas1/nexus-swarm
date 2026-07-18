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
- **[learning_notes.md](file:///c:/hack/learning_notes.md)** *(Excluded from git tracking)*: Practical lessons on AutoGen state synchronization, prototype pollution prevention, and NIM routing optimizations.
- **[interview_notes.md](file:///c:/hack/interview_notes.md)** *(Excluded from git tracking)*: Structural design review notes, engineering tradeoffs, and conceptual Q&As.

---

## 🛠️ Technology Stack

| Layer | Technology |
| :--- | :--- |
| **Agent Framework** | Microsoft AutoGen v0.4 (`autogen-agentchat`, `autogen-ext`) |
| **Primary LLM** | NVIDIA NIM API (`mistralai/mistral-large-3`, `qwen2.5-coder-32b`, `mistral-nemo-12b`) |
| **Development LLM** | Ollama local API fallback (`gemma`, `qwen`) |
| **Tool Interface** | Model Context Protocol (stdio servers: `logger_mcp`, `security_mcp`, `quality_mcp`, `pipeline_status_mcp`) |
| **Backend** | FastAPI, SQLAlchemy 2.0 (Async), Pydantic v2 |
| **State & Cache** | Redis (pub/sub logs and AutoGen state cache) |
| **Relational Storage** | PostgreSQL 15 / Local SQLite fallback |
| **Semantic Memory** | PostgreSQL `pgvector` with 1024-dimension embeddings |
| **Frontend UI** | React 18, Vite, Tailwind CSS v4, Zustand v4, React Flow, Monaco Editor |

---

## 🚀 Quick Start (Docker Compose)

### 1. Clone & Configure
```bash
git clone https://github.com/theshauryas1/nexus-swarm.git
cd nexus-swarm
cp .env.example .env
```

Edit your `.env` to supply either your `NVIDIA_API_KEY` or `AZURE_OPENAI_API_KEY`.

### 2. Launch Services
```bash
docker compose up --build
```

- **Dashboard**: `http://localhost:3000`
- **Backend API**: `http://localhost:8000`
- **API Swagger Docs**: `http://localhost:8000/docs`
