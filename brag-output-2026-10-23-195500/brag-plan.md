# Brag Plan: NexusSwarm v2 (Extended Architecture Edition)

## What is this app?
**NexusSwarm v2** is an autonomous multi-agent operating system that organizes 28 specialized AI agents into enterprise engineering divisions (Executive → 5 Managers → Sandboxed Workers) to plan, write, test, secure, and deliver software under runtime tool-layer governance.

## The angle
Most multi-agent frameworks are flat, fragile prompt chains that hallucinate fake packages, leak credentials, and break in real terminal environments. NexusSwarm mirrors enterprise corporate engineering divisions: 
- An **Intelligent Model Router** slashes generation latency by **62%** on NVIDIA NIM by matching tasks to right-sized models (Nemotron-3 Super 120B, Llama 3.2 11B Vision, Nemotron-3 Nano/Lightning) with Google Gemini cloud failover.
- A **5-Tier Memory Pyramid** anchors cross-task learning using PostgreSQL 15 ACID storage and `pgvector` 1024-dimension embeddings (`llama-nemotron-embed-vl-1b`).
- **AST Analysis** intercepts hallucinated dependencies before execution.
- An **Autonomous QA Repair Loop** patches test tracebacks without human prompts.
- Evaluated on a **107-task benchmark suite** across 9 domains with 4 live attack vectors blocked.

---

## Storyboard (52.0 Seconds / 7 Scenes)

### Scene 1: The Hook & Core Value Proposition (0.0s – 7.4s)
- **Visual**: Glowing emerald status badge: `ENTERPRISE AI ENGINEERING OPERATING SYSTEM`. Hero typography: `NexusSwarm v2`. Subtitle: `Hierarchical Multi-Agent Governance Mirrored from Real Engineering Divisions`.
- **Stat Cards**: 28 Agents (3 Governance Tiers), -62% Latency (Dynamic Model Router), 107 Tasks (Evaluated Benchmarks), Zero Vetting Leaks (Enforced Tool Security).
- **Sound**: Resonant C2 sub-bass pulse with stereo atmospheric pads.

### Scene 2: 3-Tier Governance Hierarchy & Agent Roles (7.4s – 14.8s)
- **Visual**: 3-column organizational topology card grid:
  - **Level 1 (Executive)**: `HeadOrchestrator` (DAG subtask decomposition, conflict resolution) & `TokenBudgetManager` (cost & token caps).
  - **Level 2 (Management Tier)**: `PlanningManager` (specs & risk register), `EngineeringManager` & `QAManager` (code coordination & pytest triage), and `SecurityManager` (holds **strict hard veto** over DevOps deployments).
  - **Level 3 (Sandboxed Workers)**: `BackendAgent`, `APIAgent`, `TestAgent`, `ScannerAgent`, `DeployAgent`.
- **Sound**: Division fan-out impact hit with rising arpeggiated synths.

### Scene 3: Intelligent Model Router & LLM Infrastructure (14.8s – 22.2s)
- **Visual**: 4 model routing cards:
  - `nvidia/nemotron-3-super-120b`: Executive Orchestration, Planning, and Security Governance.
  - `meta/llama-3.2-11b-vision-instruct`: Full-Stack Code Generation, API Contracts, Engineering.
  - `nvidia/nemotron-3-nano-30b & 3.5-lightning`: Pipeline Telemetry & State Coordination.
  - `google/gemini-2.0-flash & gemini-1.5-pro`: Zero-latency cloud failover & consensus.
- **Metric Highlight**: Massive `-62%` Task Latency Reduction (cut from ~45.2s down to ~17.1s).
- **Sound**: Frequency glide sub-drop from 500Hz to 70Hz.

### Scene 4: 5-Tier Memory Pyramid & Database Architecture (22.2s – 29.6s)
- **Visual**: Interactive 5-tier memory pyramid:
  - Tier 1: Ephemeral Context (Token Window & Top-K RAG)
  - Tier 2: Real-Time Working State (Redis 7 Pub/Sub & Pipeline Locks)
  - Tier 3: Relational Audit Trail (PostgreSQL 15 ACID on Google Cloud SQL)
  - Tier 4: Long-Term Semantic Vector Memory (PostgreSQL + `pgvector` with 1024-dim Cosine Distance `<=>`)
  - Tier 5: Workspace Artifact Persistence (Local files & Google Cloud Storage)
- **MCP Tool Tier**: Insulated stdio servers (`logger_mcp`, `security_mcp`, `quality_mcp`, `pipeline_status_mcp`).
- **Sound**: Low 90Hz resonant impact hit with rich stereo chords.

### Scene 5: Runtime Guardrails & Self-Healing QA Loop (29.6s – 37.0s)
- **Visual**: Two side-by-side terminal simulation frames:
  - **Left (AST Import Guardrail)**: Statically parses AST, identifies `superauth_enterprise_pro`, and triggers immediate security block before terminal execution.
  - **Right (Self-Healing QA Loop)**: Detects pytest assertion failure → QAManager triages traceback → BackendAgent applies surgical patch → `pytest tests/ -v` passes 12/12 tests green.
- **Sound**: Crisp alert dissonance tone followed by a crystal pure E5 chime (659Hz) on test resolution.

### Scene 6: Objective Benchmarks & Resilience Metrics (37.0s – 44.4s)
- **Visual**: 4 empirical evidence cards:
  - `107 Tasks / 9 Categories`: Adversarial, Hallucination, Security, Self-Repair, Auth, Backend, Docker, Deployment, WebSocket.
  - `4 / 4 Attacks Neutralized`: Live resilience suite blocked prompt injection (`T03`), hallucination trap (`T02`), RCE eval (`T05`), CVE exploits (`T10`).
  - `62% Time Saved`: Dynamic model routing verified in production.
  - `100% Vetted Code`: Strict 4-eyes principle. No unvetted code builds or deploys.
- **Sound**: Driving electronic percussion and 110Hz rhythmic impact.

### Scene 7: Production Deployment & Source-Available CTA (44.4s – 52.0s)
- **Visual**: Google Cloud Run production showcase with live URLs:
  - Frontend IDE Dashboard: `nexusswarm-frontend-...run.app`
  - Backend REST / WS API Docs: `nexusswarm-backend-...run.app/docs`
  - GitHub Repository: `github.com/theshauryas1/nexus-swarm`
  - Author: **Shaurya Sharma**
- **Punchline**: "Source-available for evaluation & review • Explore the architecture."
- **Sound**: Resolving C5 crystal tone and smooth master fade.

---

## Technical Specs
- **Resolution**: 1920x1080 (1080p Full HD)
- **Framerate**: 30.0 fps (1560 frames total)
- **Duration**: 52.0 seconds
- **Audio**: 48,000 Hz, 16-bit Stereo WAV synthesized via NumPy/SciPy
- **Video Codec**: H.264 (High Profile, YUV420p, CRF 18, faststart enabled)
- **Audio Codec**: AAC-LC @ 192 kbps
- **Poster**: 1920x1080 JPEG baked into frame 0 and saved as `brag.jpg`
