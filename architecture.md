# NexusSwarm v2 — System Architecture & Multi-Agent Design

This document details the multi-agent orchestration, state routing, standard interfaces, and custom Model Context Protocol (MCP) servers powering **NexusSwarm v2**.

---

## 1. Governance Architecture

NexusSwarm replaces standard, flat single-agent flows with a strict **hierarchical governance model**. Security, quality, and routing rules are enforced at the tool and sandbox level, preventing agents from bypassing policies simply by altering their prompt history.

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

### Governance Tiers
1. **Executive Tier (`HeadOrchestrator`)**: Receives the top-level user task (e.g. "Build a REST API"), decomposes it into logical sub-tasks, assigns them to appropriate Managers, and acts as the final decision authority for escalations/conflicts.
2. **Manager Tier (`PlanningManager`, `EngineeringManager`, etc.)**: Translates task plans into worker instructions, manages worker state, aggregates results, and validates work against quality thresholds.
3. **Worker Tier (`BackendAgent`, `TestAgent`, etc.)**: Operates within a terminal sandbox, writes files, installs dependencies, and runs tests.

---

## 2. Multi-Agent Framework (AutoGen v0.4)

The agent layer is built on Microsoft's **AutoGen v0.4** (`autogen-agentchat` and `autogen-ext` packages). 

- **State Persistence**: Redis caches the multi-agent conversation states, allowing runs to be paused, resumed, or inspected.
- **Model Routing**: Handled in [llm_factory.py](file:///c:/hack/backend/agents/llm_factory.py). The system dynamically routes agent queries to the appropriate NIM model depending on role complexity:
  - Orchestration & Decomposition → `deepseek-ai/deepseek-v4-flash`
  - Code Generation → `qwen/qwen2.5-coder-32b-instruct`
  - Simple Workers & Scanning → `nv-mistralai/mistral-nemo-12b-instruct`

---

## 3. Tool Tier & Custom MCP Servers

Rather than giving agents direct, unsafe access to the host machine, all terminal commands and file edits flow through Model Context Protocol (MCP) servers. The tool layer enforces security rules:

| Server | Tools | Description | Target Agent |
| :--- | :--- | :--- | :--- |
| `logger_mcp` | `log_agent_action`<br>`broadcast_event` | Publishes live event updates to Redis channels for WebSocket clients. | All Agents |
| `security_mcp` | `scan_for_secrets`<br>`scan_file` | Audits files for hardcoded credentials, keys, or security patterns. | ScannerAgent |
| `quality_mcp` | `lint_python`<br>`estimate_test_coverage` | Lints generated code, calculates cyclomatic complexity, and checks test coverage. | TestAgent |
| `pipeline_status_mcp`| `get_pipeline_health`<br>`update_pipeline_progress`| Reads database tables to report pipeline health back to the Orchestrator. | HeadOrchestrator |

---

## 4. Diagnostics & Self-Correction Loops

If a worker agent fails a task (e.g., test suite fails, or linter returns syntax errors), the manager does not immediately abort. Instead, it enters a self-correction loop:

1. **Test Failure**: `TestAgent` runs pytest and detects a failing assertion.
2. **Triage**: The `QAManager` parses the traceback and identifies the problematic file and line numbers.
3. **Escalation**: `QAManager` sends a patch request to `EngineeringManager`.
4. **Execution**: `BackendAgent` rewrites the buggy code segment.
5. **Re-Test**: `TestAgent` re-execures pytest. If it fails again, the loop repeats up to `max_agent_retries` (configured to 3). If it succeeds, progress moves to the next gate.
