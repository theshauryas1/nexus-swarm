# NexusSwarm v2 — System Design & Engineering Interview Notes

This document contains conceptual notes, architectural tradeoffs, and system design questions discussed during the design and review of the **NexusSwarm v2** platform.

---

## 1. Architectural Tradeoffs

### 1.1. Hierarchical Multi-Agent Governance vs. Flat Auto-Routing Swarms
- **Hierarchical Governance (NexusSwarm)**:
  - *Pros*: Clear ownership, deterministic checkpoints (e.g. Security Agent can block DevOps Agent), structured logs matching real-world engineering teams, easily understood by stakeholders.
  - *Cons*: Higher latency due to communication overhead between parent managers and child workers, increased LLM call overhead for orchestration turns.
- **Flat Swarms (e.g. ChatRoom/GroupChat)**:
  - *Pros*: Fast execution, agents can jump in asynchronously, less rigid.
  - *Cons*: High hallucination rates, conversation drift, hard to enforce strict security gates, difficult to construct a structured visual DAG.

### 1.2. Local Ollama vs. Cloud-Based NVIDIA NIM API
- **Local Ollama**:
  - *Pros*: Zero cost, offline support, absolute data security for local codebases.
  - *Cons*: Bound by local GPU resources (running large models like Qwen 32B Coder is extremely slow on standard developer laptops).
- **NVIDIA NIM (Cloud API)**:
  - *Pros*: Instant access to state-of-the-art enterprise models (Llama 3.3 70B, Qwen 2.5 Coder 32B), low latency, no local compute requirements.
  - *Cons*: Pay-per-token API cost, requires network connection, data transits outside local boundaries.

### 1.3. Relational Memory (PostgreSQL pgvector) vs. Graph Database (Neo4j)
- **PostgreSQL pgvector (Current)**:
  - *Pros*: Simplified infrastructure (uses the same Postgres database that stores task states), fast cosine similarity queries over text chunks.
  - *Cons*: Hard to query multi-hop relationships (e.g. "Find all files written by BackendAgent that were rejected by TestAgent due to a SQL injection vulnerability").
- **Graph Database (Planned)**:
  - *Pros*: Excellent for indexing semantic agent hops, tracking structural lineages, and querying complex agent relationships.
  - *Cons*: Introduces extra operational complexity, requires managing database syncs.

---

## 2. Technical Q&A

### Q1: How does the system guarantee that generated code is secure without relying entirely on LLM prompts?
- **Answer**: Governance is enforced at the **tool/sandbox layer** using the custom `security_mcp` server. Even if a `CoderAgent` writes insecure code, the `ScannerAgent` executes static code analysis tools (such as Bandit and secret scanners) on the file system. If the security check fails, the pipeline is locked, and a block event is logged in `pipeline_health`. The `DevOpsAgent` cannot access deploy tools until `SecurityManager` clears the warning flag in the DB.

### Q2: Explain the mechanism behind the live observability terminal.
- **Answer**: When an agent performs a tool action (e.g. running tests or writing code), it calls `logger_mcp.log_agent_action`. The backend handler writes this record to `agent_logs` in Postgres and simultaneously publishes the event payload to a Redis pub/sub channel. The FastAPI API Gateway listens on this channel and broadcasts the JSON events over active WebSocket connections (`/ws/agents`) to the React dashboard, which updates the Zustand store and React Flow canvas dynamically in under 150ms.

### Q3: How does the model router prevent rate limit blocks (`429`) when many workers run concurrently?
- **Answer**: The backend implements an IP-based token bucket limiter inside [llm_guardrails.py](file:///c:/hack/backend/llm_guardrails.py). Before launching a task, the route estimates the total token usage and verifies the client IP has budget remaining. Additionally, the router paces LLM calls, enforcing a serialization lock to ensure concurrent workers delay their requests slightly, avoiding massive parallel spikes.
