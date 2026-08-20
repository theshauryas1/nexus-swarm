# NexusSwarm v2 — Memory Architecture & Context Strategy

This document details the multi-tier memory system, vector storage, embedding models, chunking strategies, and context isolation mechanisms used across **NexusSwarm v2**.

---

## 1. Executive Overview: Memory as the Swarm Moat

NexusSwarm utilizes a **persistent, multi-tier memory engine** to prevent context loss, enable cross-task learning, and eliminate recurring software engineering mistakes. Instead of treating each task execution as an isolated session, the memory architecture captures architectural patterns, coding guidelines, security mitigations, and past debugging resolutions, feeding them back into downstream agent prompts.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        NEXUSSWARM MEMORY PYRAMID                       │
├────────────────────────────────────────────────────────────────────────┤
│  Tier 1: Ephemeral Prompt Context (LLM Token Window & Guardrails)      │
│  Tier 2: Real-Time Working State (Redis 7 Pub/Sub & Session Cache)     │
│  Tier 3: Relational & Audit Memory (PostgreSQL 16 / Cloud SQL / SQLite)│
│  Tier 4: Long-Term Semantic Vector Memory (PostgreSQL + pgvector)      │
│  Tier 5: Workspace Artifact Persistence (Local Workspace & GCS)        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. The 5-Tier Memory Hierarchy

| Memory Tier | Storage Engine | Scope & Retention | Key Data Stored | Primary Consumers |
| :--- | :--- | :--- | :--- | :--- |
| **Tier 1: Prompt & LLM Context** | Volatile RAM / Model Window | Single Inference Call | System prompts, active conversation turns, sanitized user input, top-k retrieved memories | Active LLMs via [llm_factory.py](file:///d:/hack/backend/agents/llm_factory.py) |
| **Tier 2: Real-Time Working State** | Redis 7 (`redis-alpine`) | Task Run Lifecycle | Pipeline locks, agent step statuses, live Pub/Sub WebSocket event stream | [redis_client.py](file:///d:/hack/backend/memory/redis_client.py), WebSocket routes |
| **Tier 3: Relational Audit Trail** | PostgreSQL 16 / SQLite | Permanent (ACID) | `tasks`, `pipelines`, `agent_logs`, `pipeline_health`, `conflicts`, `model_performance` | Orchestrators, Managers, Dashboards |
| **Tier 4: Long-Term Semantic Memory** | PostgreSQL + `pgvector` | Permanent | 1024-dim vector embeddings of past decisions, code patterns, security standards, review feedback | [MemoryEngine](file:///d:/hack/backend/engines/memory_engine.py), Agents |
| **Tier 5: Workspace Artifacts** | Local Filesystem & GCS | Permanent | Generated source code, pytest suites, OpenAPI specs, Dockerfiles, reports | [file_storage.py](file:///d:/hack/backend/memory/file_storage.py), Sandbox runtime |

---

## 3. Vector Database & Embedding Strategy

### 3.1. Vector Store: PostgreSQL with `pgvector`
NexusSwarm integrates the [`pgvector`](https://github.com/pgvector/pgvector) extension directly into PostgreSQL 15/16.

* **Schema Definition**: Defined in [init.sql](file:///d:/hack/backend/db/init.sql#L162-L178) and [db_client.py](file:///d:/hack/backend/memory/db_client.py#L1138-L1170).
* **Distance Metric**: Cosine Distance (`<=>`), calculating similarity via `(1 - (embedding <=> :query_embedding::vector))`.
* **Hybrid Relational Queries**: Allows combining metadata filters (`memory_type`, `source_task_id`, `confidence_score`) with semantic vector similarity in a single ACID query.

```sql
SELECT id, content, memory_type, source_task_id, confidence_score, access_count,
       (1 - (embedding <=> :query_embedding::vector)) AS similarity
FROM memories
WHERE memory_type = 'security_standard'
ORDER BY embedding <=> :query_embedding::vector
LIMIT 5;
```

### 3.2. Embedding Model: NVIDIA NIM `nvidia/embed-qa-4`
* **Provider**: NVIDIA NIM API (`integrate.api.nvidia.com/v1/embeddings`).
* **Vector Dimensions**: `1024` dimensions.
* **Specialization**: Optimized for technical documentation, code QA, and dense passage retrieval.

### 3.3. Offline / Resilient Fallback: Deterministic Pseudo-Embedding
To prevent crashes during offline development, test runs ([test_memory_engine.py](file:///d:/hack/backend/tests/test_memory_engine.py)), or when API keys are absent:
* **Algorithm**: Implemented in [memory_engine.py](file:///d:/hack/backend/engines/memory_engine.py#L22-L48). Tokenizes words and maps them via multi-bit MD5 hashing into a 1024-dim slot space, followed by $L_2$ Euclidean normalization ($\|v\|_2 = 1.0$).
* **Guarantee**: Retains deterministic keyword overlap scoring without external API dependency.

---

## 4. Chunking & Context Segmentation Strategy

### 4.1. Semantic Unit-of-Work Chunking (Context-Boundary Segmentation)
Unlike naive fixed-size token splitting (which arbitrarily cuts functions or sentences), NexusSwarm applies **Semantic Unit-of-Work Chunking**:

1. **Atomic Categorization (`memory_type`)**:
   - `architecture`: High-level system designs, database schemas, and interface boundaries.
   - `coding_standard`: Idioms, module conventions, and language-specific best practices.
   - `security_standard`: Vulnerability prevention rules (e.g., token validation, SQL injection filters, CORS).
   - `pr_review`: Code smells, review feedback, and anti-pattern alerts.
   - `conversation` / `incident_repair`: Root cause analysis, failed retry logs, and automated recovery steps.
2. **Task Provenance Isolation (`source_task_id`)**:
   - Every stored memory is linked to its originating task UUID, tracking full lineage and confidence scores.
3. **Prompt Budget Efficiency**:
   - Small, high-density atomic snippets (top 3–5 items) are dynamically injected into agent prompts, consuming less than 1,000 tokens while providing targeted context.

---

## 5. Context Isolation: LLM Context vs. Agent Context

```
┌────────────────────────────────────────────────────────────────────────┐
│                        CONTEXT BOUNDARY LAYERS                         │
├───────────────────────────────────┬────────────────────────────────────┤
│           LLM CONTEXT             │           AGENT CONTEXT            │
│  (Inside Model Token Window)      │   (Inside Swarm Orchestrator)      │
├───────────────────────────────────┼────────────────────────────────────┤
│ • System Prompt & Role Definition │ • AutoGen v0.4 Turn History        │
│ • Sanitized User Task Prompt      │ • MCP Tool Execution Bindings      │
│ • Retrieved Semantic Memories     │ • Pipeline Lifecycle State         │
│ • Input/Output Security Filters   │ • Worker Subtask Delegation Graph  │
│ • Token Usage & Cost Caps         │ • Failure/Retry Counter State      │
└───────────────────────────────────┴────────────────────────────────────┘
```

### 5.1. LLM Context Safeguards
- **Input Sanitization**: Pre-processes user inputs via [llm_guardrails.py](file:///d:/hack/backend/llm_guardrails.py) and [security_utils.py](file:///d:/hack/backend/security_utils.py) to block prompt injections and secret leaks.
- **Output Sanitization**: Strips dangerous executable payloads or XSS vectors before relaying outputs back to agents.
- **Model Router Allocation**: Dynamically assigns token limits based on model capacity (e.g., 4096 tokens for complex code generation with Qwen Coder; 1024 tokens for coordination with Llama-3.1 8B).

### 5.2. Agent Execution Context
- **AutoGen Turns**: Manages multi-turn conversations between managers and workers without polluting global memory.
- **Model Context Protocol (MCP)**: Limits agent interactions to strictly sandboxed tools (`read_file`, `write_file`, `lint_python`, `run_pytest`, `search_memory`).

---

## 6. End-to-End Memory Data Flow

```
[Agent Action / Review / Plan]
             │
             ▼
    [MemoryEngine.add_memory()]
             │
             ├──(1) Generate 1024-dim embedding via NVIDIA NIM (nvidia/embed-qa-4)
             │      * Fallback: Compute 1024-dim normalized Min-Hash pseudo-embedding
             ▼
    [PostgreSQL memories Table]
             │  (2) Persists content, vector, memory_type, task_id, confidence_score
             │
             ▼
[New Agent Task Initiated]
             │
             ├──(3) Query: "JWT authentication token revocation"
             ▼
    [MemoryEngine.semantic_search()]
             │  (4) Embeds query -> Cosine distance ranking (<=>) in pgvector
             ▼
    [Top-K Semantic Matches]
             │  (5) Injected into Agent System/User Prompt as context
             ▼
    [Agent Generates Code with Learned Standards]
```

---

## 7. Justification Matrix vs. Alternative Approaches

| Requirement | NexusSwarm Choice | Alternative Option | Justification for NexusSwarm Choice |
| :--- | :--- | :--- | :--- |
| **Vector Database** | **PostgreSQL + `pgvector`** | Pinecone / Weaviate / Milvus | • Single source of truth (no dual-write bugs).<br>• Relational joins between memories and tasks.<br>• Zero extra infrastructure overhead in Cloud SQL and Docker. |
| **Local Development** | **SQLite + Fallback Text / Vectors** | ChromaDB / FAISS Server | • Self-contained single file database with zero network ports.<br>• Identical SQLAlchemy API abstraction without running background daemons. |
| **Embedding Engine** | **NVIDIA NIM `nvidia/embed-qa-4`** | OpenAI `text-embedding-3-small` | • Provider consolidation with all NIM LLMs.<br>• High-accuracy technical text and code retrieval.<br>• Enterprise VPC and private deployment support. |
| **Chunking Logic** | **Semantic Unit-of-Work (Atomic)** | Fixed Sliding Token Window (e.g. 500 tokens) | • Preserves complete architectural blocks and code functions.<br>• Eliminates broken syntax and context truncation. |
| **Working Memory Bus** | **Redis 7 In-Memory** | RabbitMQ / Kafka | • Native key-value caching + ultra-low-latency pub/sub for WebSockets.<br>• Low resource footprint. |
