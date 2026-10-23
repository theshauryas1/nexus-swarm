# NexusSwarm v2 — Developer Learning Notes

This document contains practical developer insights, debugging logs, architectural gotchas, and learning experiences from building **NexusSwarm v2**.

---

## 1. AutoGen v0.4 State Synchronization

### Challenge
During concurrent task execution, multiple worker agents spawn threads or async loops that report updates. Initial implementations ran into race conditions where Redis conversation histories got out of sync, leading to duplicated agent replies or skipped quality checks.

### Resolution
- Transitioned to explicit transactional state locks over Redis keys when calling AutoGen's `AgentChat` interface.
- Implemented state checkpoints inside [db_client.py](file:///c:/hack/backend/memory/db_client.py). Each agent turn saves its thread context to PostgreSQL before releasing the Redis execution lock, ensuring full history recovery even if a worker container restarts mid-run.

---

## 2. Frontend Prototype Pollution Defenses

### Challenge
Frontend vulnerability scanning flagged dynamic object updates inside the file explorer (`📁` directory navigation) as susceptible to prototype pollution. Because folder trees are constructed recursively from variable database lists, bracket notations like `tree[part] = {}` were prone to exploits if a task was named `__proto__`.

### Resolution
- Enforced prototype-safe object instantiation using `Object.create(null)` for all recursive tree nodes.
- Created static lookup helpers inside the React components to isolate dynamic path evaluations, preventing malicious workspace names from overriding prototype values.

---

## 3. NIM Model Routing & Latency Optimization

### Challenge
Routing all agent tasks to a massive model like `mistralai/mistral-large-3-675b-instruct` resulted in slow pipeline runs (averaging 45+ seconds for simple code evaluations). Conversely, using small models for HeadOrchestrator decomposition resulted in poor task segmentation and missing requirements.

### Resolution
- Implemented the dynamic Model Router in [model_router.py](file:///c:/hack/backend/engines/model_router.py). 
- Tasks are categorized at execution time:
  - Complex architectural reasoning and task planning route to large, high-capacity models (`mistral-large` or `deepseek-v4`).
  - Python coding and React TSX assembly route to high-efficiency coding specialists (`qwen2.5-coder-32b`).
  - Standard validation, secrets scanning, and linter logging tasks route to fast, cheap models (`mistral-nemo-12b`).
- This reduced average end-to-end task execution times by **62%** while maintaining correct code compilation rates.

---

## 4. API Rate Limit Backoff Pacing

### Challenge
Running deep agent hierarchies (Planning → Engineering → QA → Security) simultaneously triggers multiple downstream API calls to external NIM or Azure endpoints. Under heavy loads, these concurrent requests frequently hit `429 Too Many Requests` limits, halting the swarm run.

### Resolution
- Enforced pace-queuing in [llm_guardrails.py](file:///c:/hack/backend/llm_guardrails.py).
- Requests from workers are serialized and must wait for a minimum cooling interval (`MIN_INTERVAL_SECONDS = 0.5`) if they are triggered concurrently by the same client IP.
- Combined the pacing wrapper with exponential backoff retry cycles up to 3 times before raising a pipeline alert.
