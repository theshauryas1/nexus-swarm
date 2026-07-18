# Developer Onboarding Guide

Welcome to the **NexusSwarm v2** workspace! This guide walks you through setting up your local development environment, running tests, launching services via Docker, and executing benchmark scripts.

---

## 1. Local Development Setup

### 1.1. System Requirements
- **Python**: Version 3.11 recommended.
- **Node.js**: Version 18+ and npm installed.
- **Docker Desktop**: Required to run database (PostgreSQL), cache (Redis), and local LLM (Ollama) infrastructure containerized.
- **API Keys**: Access key for **NVIDIA NIM** (`NVIDIA_API_KEY`) or **Azure OpenAI** (`AZURE_OPENAI_API_KEY`) to enable live agent runs.

### 1.2. Backend Installation
1. Navigate to the project directory:
   ```bash
   cd nexusswarm
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   # Windows (PowerShell):
   .\.venv\Scripts\Activate.ps1
   # macOS/Linux:
   source .venv/bin/activate
   ```
3. Install the dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```
4. Copy the environment template and configure your keys:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` to supply:
   - `NVIDIA_API_KEY` (if using NVIDIA NIM)
   - `AZURE_OPENAI_API_KEY` + `AZURE_OPENAI_ENDPOINT` (if using Azure OpenAI)
   - `LLM_PROVIDER="auto"` (routes dynamically between available endpoints)
5. Start the FastAPI development server:
   ```bash
   uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
   ```
   The interactive Swagger documentation will be available at `http://localhost:8000/docs`.

### 1.3. Frontend Installation
1. Open a new terminal window and navigate to the frontend folder:
   ```bash
   cd frontend
   ```
2. Install Node packages:
   ```bash
   npm install
   ```
3. Run the development server:
   ```bash
   npm run dev
   ```
   The dashboard UI will be live at `http://localhost:3000`.

---

## 2. Docker Compose Environment (All-in-One)

To spin up the entire system including PostgreSQL, Redis, Frontend, and Backend with hot-reloading:

```bash
docker compose up --build
```

**Services Mapping**:
- Frontend Dashboard: `http://localhost:3000`
- Backend API Gateway: `http://localhost:8000`
- Nginx Proxy: `http://localhost:80`

---

## 3. Validation & Testing

### 3.1. Running the Test Suite
Ensure your virtual environment is active, then run:
```bash
cd backend
pytest -v
```
This will run the entire suite of agent routing, database, and token budget tests.

### 3.2. Running Script Utilities
The project includes specialized development scripts located in [backend/scripts](file:///c:/hack/backend/scripts/):

- **Test NIM Pipeline**: Verifies that your NVIDIA NIM API key is working and model endpoints are reachable:
  ```bash
  python backend/scripts/test_nim_pipeline.py
  ```
- **Run SuperAuth Test**: Audits Google authentication integration and role mapping checks:
  ```bash
  python backend/scripts/run_superauth_test.py
  ```
- **Execute Agent Benchmarks**: Measures agent decomposition latency, token consumption, and success rates:
  ```bash
  python backend/scripts/run_benchmarks.py
  ```
- **Audit Dependencies**: Analyzes packages for vulnerabilities and security scans:
  ```bash
  python backend/scripts/audit_deps.py
  ```
- **Sanitize Workspace**: Clears temporary code file outputs from the sandboxed environment:
  ```bash
  python backend/scripts/sanitize_workspace.py
  ```
