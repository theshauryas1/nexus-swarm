# ⬡ NexusSwarm — Product Requirements Document (PRD)

## 1. Executive Summary & Vision
**NexusSwarm** is a state-of-the-art, enterprise-grade hierarchical multi-agent orchestration ecosystem designed to revolutionize automated software development. Mirroring a real-world enterprise engineering division, NexusSwarm leverages a structured tier of executive orchestrators, pipeline managers, specialist workers, and safety gateways to decompose, write, test, scan, and deploy high-quality software architectures.

### The Core Vision
To provide a highly visual, secure, and interactive dark-themed IDE experience where humans can launch, monitor, inspect, and guide complex multi-agent swarms. Every development task is treated as a trackable, repeatable project session, equipped with long-term memory, self-correcting diagnostics, and robust deployment compliance.

---

## 2. Product Objectives & Value Proposition
* **Hierarchical Governance over Flat Pipelines**: Replaces flat single-agent pipelines with a structured multi-tier organization (Executive → Manager → Specialist), enforcing boundaries, approvals, and quality gates.
* **Continuous Visual Feedback**: Provides a high-fidelity visual dashboard incorporating real-time interactive React Flow graph visualization, live terminal event streams, and collapsible multi-session file explorers.
* **Autonomous Self-Correction (QA & Diagnostics)**: Runs generated code in isolated environments, triages errors, and generates automatic patches using a dedicated Manager-Worker diagnostics loop.
* **GCP Cloud-Native Architecture**: Integrates directly with Google Cloud Platform, providing zero-config deployments to Google Cloud Run with robust storage and database persistence.
* **Prototype Pollution Protection & Secure Coding**: Built from the ground up with defensive engineering principles, resolving standard frontend security scanning vulnerabilities.

---

## 3. User Personas & Target Audience

### 3.1. Developer / Software Engineer (Persona: "Devin")
* **Need**: Rapid prototyping, modular microservice generation, and automated test suite creation.
* **Pain Point**: Spends excessive time writing repetitive boilerplate code, configuring Docker environments, and setting up initial test coverage.
* **NexusSwarm Solution**: Devin inputs a prompt (e.g. "Build a secure FastAPI task system"), watches Backend/API/Frontend agents compile the modules, and selects the files directly inside the Monaco editor.

### 3.2. DevOps / Release Engineer (Persona: "Clara")
* **Need**: Secure deployment pipelines, proper dependency locked builds, and GCS/SQL containerized management.
* **Pain Point**: Unverified code is deployed with potential security exploits, hardcoded secrets, or runtime environment crashes.
* **NexusSwarm Solution**: Security gates audit dependencies and scanned variables. Code is only promoted once DevOps and Gateway approval metrics clear the criteria.

### 3.3. Product / Project Manager (Persona: "Marcus")
* **Need**: Transparent progress monitoring, executive summarization, and task session sharing.
* **Pain Point**: AI pipelines are "black boxes" where it is impossible to see intermediate steps or review how resources are spent.
* **NexusSwarm Solution**: Marcus views the live execution graph, downloads completed packages as ZIP archives, and shares workspace links via direct URL query parameters.

---

## 4. Key Functional Features & Scope

### 4.1. Core Swarm Orchestration (Phase 7 Hierarchy)
A 28-agent hierarchy coordinated via **NVIDIA NIM API** endpoints (utilizing optimized Llama 3.3 70B and Llama 3.1 8B models):
* **Planning Pipeline**: requirement extraction (`requirements.md`) and risk profiling (`risk_analysis.md`).
* **Engineering Pipeline**: generates python backend (`backend.py`), OpenAPI specification (`openapi.yaml`), and frontend views (`components.tsx`).
* **QA & Diagnostics Pipeline**: automated test generation (`test_backend.py`), code execution, log triage, and patch loops.
* **Security Pipeline**: static analysis scans, dependency auditing, and gateway blocking logic.
* **Human Approval Gateway**: simulation-based gateway requiring secure token clearance.
* **DevOps & Reliability Pipeline**: Cloud container building, deployment scripts, and long-term memory updates (`knowledge.md`).

### 4.2. VS Code-Style Multi-Session File Explorer
* **Collapsible Folders**: Lists tasks/sessions as directory folders (`📁` / `📂`) dynamically fetched from the PostgreSQL backend.
* **Developer Icons**: Renders custom icons for code extensions (`🐍` Python, `⚛️` React TSX, `🐳` Dockerfile, `📋` Configuration, `📝` Markdown).
* **Fuzzy Real-time Search**: Quick text filter input in the sidebar to filter folders and nested files on the fly.
* **Dynamic Context Switching**: Clicking on a folder's file switches the workspace context and populates the Monaco editor instantly.
* **ZIP Archive Downloads**: Floating download button next to each directory folder triggers an on-the-fly zip creation and download.

### 4.3. Interactive Live Terminal Panel & Open Cloud Shell
* **Real-time Logs Feed**: WebSocket-streamed output showing accurate status symbols (`▶`, `✓`, `✗`, `○`), timestamps, and level colors.
* **Open Cloud Shell Integration**: Clickable button that launches Google Cloud Shell in a secure target frame to execute commands.
* **Interactive Command Palette**: Triggerable via `Ctrl+Shift+P` allowing tasks to be initiated without standard forms.

### 4.4. State-of-the-Art React Flow Graph
* **Visual States**: Custom ReactFlow nodes representing managers, executives, and specialists with pulsing status signals.
* **Animated Edges**: Connection lines between nodes light up and animate in the color of the active pipeline.
* **Legend Overlay**: Explains status dots (`bg-indigo-400 animate-pulse` for active, `bg-emerald-400` for done, etc.).

---

## 5. Non-Functional Requirements (NFRs)

### 5.1. Performance & Latency
* **WebSocket Heartbeats**: Feed updates must reflect in the terminal within **150ms** of the backend producing an event.
* **Large File Loading**: The editor must load files up to **2MB** in under **200ms**.
* **Database Query Performance**: Tree navigation queries must load in under **100ms** utilizing optimized task-indexing schemas.

### 5.2. Security & Compliance
* **Prototype Pollution Protection**: Strictly forbid direct brackets object lookups with variables; use prototype-safe lookup helpers throughout the application.
* **Headless Security Checks**: Prevent execution of arbitrary scripts on Cloud Run containers; ensure testing runs in sandboxed pipelines.
* **Data Privacy**: Encrypt db connections at rest and in transit via Cloud SQL IAM authenticators.

### 5.3. Reliability & Fallbacks
* **Dual-replica Storage**: Concurrently save to local disk workspace (for temporary speed) and Google Cloud Storage (for multi-replica persistence).
* **Graceful GCS Degradation**: If storage bucket connection times out, fall back cleanly to local filesystem disk storage without throwing critical server crash errors.

---

## 6. User Journeys & App Flows

```
[User inputs task in Command Palette]
       │
       ▼
[HeadOrchestrator generates plan]
       │
       ▼
[Planning Pipeline active: requirement.md + risk.md generated]
       │
       ▼
[Engineering Pipeline active: backend.py + openapi.yaml + components.tsx generated]
       │
       ▼
[QA Pipeline runs test_backend.py: tests fail -> repair loop -> patch -> tests pass]
       │
       ▼
[Security Pipeline performs static scans: no CVE -> allow gateway]
       │
       ▼
[Human Approval Gateway signed off]
       │
       ▼
[DevOps Pipeline compiles Docker container & deploys to Cloud Run]
       │
       ▼
[Reliability Pipeline writes knowledge.md -> task marked 'complete']
```

---

## 7. Metrics & Analytics Success Criteria
* **Deployment Success Rate**: Target `> 95%` automated Cloud Build deployments without container boot crashes.
* **Average Repair Time**: QA repair loop must successfully patch syntax and dependency errors in under **3 iterations** on average.
* **User Engagement**: Zero active browser warnings and zero TypeScript compilation errors in frontend builds.
