"""
llm_factory.py — NexusSwarm LLM Provider
All model IDs LIVE-TESTED against build.nvidia.com (May 2026)

Provider: NVIDIA NIM (free tier, OpenAI-compatible)
Only models that returned HTTP 200 for this account are used.
"""

import os
import logging
from pathlib import Path
from typing import Optional
from openai import AsyncOpenAI

# Load .env from the backend directory automatically
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(_env_path, override=False)

# Security helpers — sanitize inputs/outputs, track token budgets
from security_utils import (
    sanitize_llm_input,
    sanitize_llm_output,
    record_token_usage,
)
from llm_guardrails import (
    check_and_sanitize_input,
    check_and_sanitize_output,
)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
#  VERIFIED MODEL IDs  (live-tested — only these returned 200)
# ─────────────────────────────────────────────────────────────

# Reasoning / Orchestration  (675B MoE, strong reasoning)
MISTRAL_LARGE  = "mistralai/mistral-large-3-675b-instruct-2512" # HeadOrchestrator, SecurityManager
LLAMA_70B      = MISTRAL_LARGE                          # Keep variable for compatibility

# Fast / Agentic  (DeepSeek V4 Flash — confirmed OK)
DEEPSEEK_FLASH = "deepseek-ai/deepseek-v4-flash"        # Managers, Diagnostics, Reliability

# Code Generation  (397B MoE coder — confirmed OK)
QWEN_CODER     = "qwen/qwen3.5-397b-a17b"               # All coding agents

# General Purpose  (Llama 4 Maverick — confirmed OK)
LLAMA4         = "meta/llama-4-maverick-17b-128e-instruct"  # Memory, Validators, Planning

# Lightweight  (8B, fast for simple tasks)
LLAMA_8B       = "meta/llama-3.1-8b-instruct"           # RetryCoordinator, ContractValidator


# ─────────────────────────────────────────────────────────────
#  AGENT → MODEL ASSIGNMENTS  (all using verified model IDs)
# ─────────────────────────────────────────────────────────────

AGENT_MODEL_MAP: dict[str, str] = {
    # Level 1 — Executive
    "HeadOrchestrator":         LLAMA_70B,        # Strong reasoning for orchestration

    # Level 2 — Pipeline Managers
    "PlanningManager":          LLAMA_8B,         # Coordination can use fast model
    "EngineeringManager":       LLAMA_8B,
    "QAManager":                LLAMA_8B,
    "SecurityManager":          LLAMA_70B,        # Security needs strong reasoning
    "DevOpsManager":            LLAMA_8B,
    "ReliabilityManager":       LLAMA_8B,

    # Level 3 — Planning Workers
    "RequirementAgent":         LLAMA_8B,         # General planning
    "RiskAnalyzer":             LLAMA_8B,         # General analysis

    # Level 3 — Engineering Workers
    "BackendAgent":             LLAMA_70B,        # Code generation needs 70B
    "APIAgent":                 LLAMA_70B,        # API specs need 70B
    "FrontendAgent":            LLAMA_70B,        # UI generation needs 70B

    # Level 3 — QA Workers
    "TestAgent":                LLAMA_70B,        # Test code needs 70B
    "ReviewerAgent":            LLAMA_8B,         # Code review
    "RuntimeExecutionAgent":    LLAMA_8B,         # Runtime analysis

    # Level 3 — Security Workers
    "ScannerAgent":             LLAMA_70B,        # Security audit needs strongest model

    # Level 3 — DevOps Workers
    "DeployAgent":              LLAMA_70B,        # Dockerfile / CI/CD generation

    # Level 3 — Reliability Workers
    "DiagnosticsAgent":         LLAMA_8B,         # Fast diagnostics
    "RepairAgent":              LLAMA_70B,        # Code repair
    "RetryCoordinator":         LLAMA_8B,         # Simple coordination

    # Level 3 — Utility / Cross-cutting
    "KnowledgeMemoryAgent":     LLAMA_8B,         # Memory summarization
    "HallucinationValidator":   LLAMA_8B,         # Validation
    "SemanticValidator":        LLAMA_8B,         # Validation
    "ContractValidator":        LLAMA_8B,         # Simple contract check
    "HumanApprovalGateway":     LLAMA_70B,        # Gateway needs strong reasoning
    "EvaluatorAgent":           LLAMA_70B,        # Self-measurement loop
    "CriticAgent":              LLAMA_70B,        # Self-measurement loop
    "RefinerAgent":             LLAMA_70B,        # Self-measurement loop
    "HallucinationDetectorAgent": LLAMA_8B,       # Static/dynamic import validation
}

AGENT_TO_TASK_TYPE: dict[str, str] = {
    "HeadOrchestrator": "task_decomposition",
    "PlanningManager": "coordination",
    "EngineeringManager": "coordination",
    "QAManager": "coordination",
    "SecurityManager": "security_scan",
    "DevOpsManager": "coordination",
    "ReliabilityManager": "coordination",
    "RequirementAgent": "planning",
    "RiskAnalyzer": "planning",
    "BackendAgent": "code_generation",
    "APIAgent": "code_generation",
    "FrontendAgent": "code_generation",
    "TestAgent": "testing",
    "ReviewerAgent": "refactoring",
    "RuntimeExecutionAgent": "validation",
    "ScannerAgent": "security_scan",
    "DeployAgent": "reliability",
    "DiagnosticsAgent": "diagnostics",
    "RepairAgent": "bug_fix",
    "RetryCoordinator": "coordination",
    "KnowledgeMemoryAgent": "validation",
    "HallucinationValidator": "validation",
    "SemanticValidator": "validation",
    "ContractValidator": "validation",
    "HumanApprovalGateway": "architecture",
    "EvaluatorAgent": "validation",
    "CriticAgent": "validation",
    "RefinerAgent": "refactoring",
    "HallucinationDetectorAgent": "validation",
    "ArchitectAgent": "architecture",
    "CoderAgent": "code_generation",
}


# ─────────────────────────────────────────────────────────────
#  CLIENT FACTORY
# ─────────────────────────────────────────────────────────────

def _get_client() -> AsyncOpenAI:
    """Returns AsyncOpenAI client pointed at LLM provider."""
    provider = os.environ.get("LLM_PROVIDER", "nvidia")
    if provider == "ollama":
        return AsyncOpenAI(
            base_url="http://localhost:11434/v1",
            api_key="ollama",
        )
    
    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "NVIDIA_API_KEY not set. "
            "Get a free key at build.nvidia.com → no credit card needed."
        )
    return AsyncOpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key,
    )


def get_model_for_agent(agent_name: str) -> str:
    """
    Returns the verified NIM model ID for a given agent.
    Falls back to DEEPSEEK_FLASH if agent name not found.
    """
    provider = os.environ.get("LLM_PROVIDER", "nvidia")
    if provider == "ollama":
        return "gemma4:e2b"
    model = AGENT_MODEL_MAP.get(agent_name)
    if not model:
        logger.warning(f"No model mapping for '{agent_name}' — defaulting to {DEEPSEEK_FLASH}")
        return DEEPSEEK_FLASH
    return model


# ─────────────────────────────────────────────────────────────
#  CORE INFERENCE CALL
# ─────────────────────────────────────────────────────────────

async def call_agent_llm(
    agent_name: str,
    prompt: str,
    system: Optional[str] = None,
    max_tokens: int = 2048,
    temperature: float = 0.2,
    task_id: Optional[str] = None,
) -> str:
    """
    Main inference function. Selects model dynamically via Model Router,
    calls LLM provider, and logs latency/outcome statistics.
    """
    import time
    provider = os.environ.get("LLM_PROVIDER", "nvidia")
    task_type = AGENT_TO_TASK_TYPE.get(agent_name, "default")
    
    # Resolve model dynamically
    if provider != "ollama":
        from engines.model_router import select_optimal_model
        requirements = {}
        if agent_name in ("HeadOrchestrator", "SecurityManager", "ScannerAgent"):
            requirements["min_success_rate"] = 90.0
        elif agent_name in ("BackendAgent", "APIAgent", "FrontendAgent", "ArchitectAgent", "CoderAgent"):
            requirements["min_success_rate"] = 85.0
            
        try:
            model = await select_optimal_model(task_type, requirements)
        except Exception as err:
            logger.warning(f"Model Router failed for {agent_name}: {err}. Using static mapping.")
            model = get_model_for_agent(agent_name)
    else:
        model = "gemma4:e2b"

    client = _get_client()

    # ── LLM Guardrail Check: Input
    guard_in = check_and_sanitize_input(prompt)
    if not guard_in.is_safe:
        logger.error(f"[{agent_name}] LLM Input Guardrail blocked request: {guard_in.reason}")
        raise ValueError(guard_in.reason)

    # ── Security: sanitize user-supplied prompt before forwarding
    # (prevents prompt injection; system prompt is trusted internal text)
    safe_prompt = sanitize_llm_input(guard_in.content)

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": safe_prompt})

    logger.info(f"[{agent_name}] Calling {provider} model: {model}")

    start_time = time.time()
    success = False
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        content = response.choices[0].message.content
        success = True
        
        prompt_tokens = response.usage.prompt_tokens if (response.usage and hasattr(response.usage, "prompt_tokens")) else 0
        completion_tokens = response.usage.completion_tokens if (response.usage and hasattr(response.usage, "completion_tokens")) else 0
        tokens_used = response.usage.total_tokens if (response.usage and hasattr(response.usage, "total_tokens")) else 0
        
        logger.info(f"[{agent_name}] Response received ({tokens_used} tokens)")

        # ── Security: record token usage for budget tracking
        if tokens_used:
            record_token_usage("system", int(tokens_used))

        # ── LLMOps: record task-level cost/token billing
        resolved_task_id = task_id
        if not resolved_task_id:
            try:
                from memory.cost_tracker import current_task_id
                resolved_task_id = current_task_id.get("")
            except Exception:
                pass

        if resolved_task_id and (prompt_tokens or completion_tokens):
            from memory.cost_tracker import record_task_llm_usage
            record_task_llm_usage(resolved_task_id, model, prompt_tokens, completion_tokens)

        # ── LLM Guardrail Check: Output
        guard_out = check_and_sanitize_output(content)
        if "Hallucination Warning" in guard_out.reason:
            logger.warning(f"[{agent_name}] LLM Output Guardrail warning: {guard_out.reason}")

        # ── Security: sanitize LLM output before returning (XSS defence-in-depth)
        return sanitize_llm_output(guard_out.content)

    except Exception as e:
        logger.error(f"[{agent_name}] {provider} call failed: {e}")
        raise
    finally:
        latency_ms = (time.time() - start_time) * 1000.0
        if provider != "ollama":
            try:
                from engines.model_router import log_model_outcome
                await log_model_outcome(model, task_type, latency_ms, success)
            except Exception as ex:
                logger.warning(f"Failed to log model outcome to db: {ex}")



# ─────────────────────────────────────────────────────────────
#  CONVENIENCE WRAPPERS
# ─────────────────────────────────────────────────────────────

async def orchestrator_call(prompt: str, system: str = "", task_id: Optional[str] = None) -> str:
    return await call_agent_llm("HeadOrchestrator", prompt, system, task_id=task_id)

async def manager_call(manager_name: str, prompt: str, system: str = "", task_id: Optional[str] = None) -> str:
    return await call_agent_llm(manager_name, prompt, system, task_id=task_id)

async def worker_call(worker_name: str, prompt: str, system: str = "", task_id: Optional[str] = None) -> str:
    return await call_agent_llm(worker_name, prompt, system, task_id=task_id)


# ─────────────────────────────────────────────────────────────
#  MODEL REGISTRY  (used by /agents endpoint)
# ─────────────────────────────────────────────────────────────

def get_full_model_registry() -> dict:
    """Returns the full agent→model map with metadata."""
    return {
        agent: {
            "model":    model,
            "provider": "NVIDIA NIM",
            "base_url": "https://integrate.api.nvidia.com/v1",
        }
        for agent, model in AGENT_MODEL_MAP.items()
    }
