"""
llm_factory.py — NexusSwarm LLM Provider & Dynamic Fallback Execution Engine
Live-benchmarked against NVIDIA NIM with automatic model failover and task routing.
"""

import os
import time
import logging
from pathlib import Path
from typing import Optional, List
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
#  LIVE VERIFIED MODEL IDs (Active on NVIDIA NIM 2026)
# ─────────────────────────────────────────────────────────────

# High-Reasoning & Architecture (120B MoE, Flagship NVIDIA model)
NEMOTRON_SUPER = "nvidia/nemotron-3-super-120b-a12b"

# High-Speed Code Generation & Workers (Meta Llama 3.2 11B ~0.5s latency)
LLAMA_VISION   = "meta/llama-3.2-11b-vision-instruct"

# Fast Coordination & Diagnostics (30B MoE Nano ~0.38s latency)
NEMOTRON_NANO  = "nvidia/nemotron-3-nano-30b-a3b"

# Deep Reasoning & Refactoring (30B Lightning)
NEMOTRON_LIGHTNING = "nvidia/nemotron-3.5-lightning-30b-a3b"

# Agentic Diagnostics (DeepSeek V4 Pro)
DEEPSEEK_PRO   = "deepseek-ai/deepseek-v4-pro-0813"

# Legacy alias compatibility
MISTRAL_LARGE  = NEMOTRON_SUPER
LLAMA_70B      = NEMOTRON_SUPER
DEEPSEEK_FLASH = NEMOTRON_NANO
QWEN_CODER     = LLAMA_VISION
LLAMA4         = LLAMA_VISION
LLAMA_8B       = NEMOTRON_NANO


# ─────────────────────────────────────────────────────────────
#  AGENT → MODEL ALLOTMENTS
# ─────────────────────────────────────────────────────────────

AGENT_MODEL_MAP: dict[str, str] = {
    # Level 1 — Executive
    "HeadOrchestrator":         NEMOTRON_SUPER,       # Strong reasoning for orchestration

    # Level 2 — Pipeline Managers
    "PlanningManager":          NEMOTRON_NANO,        # Ultra-fast coordination
    "EngineeringManager":       NEMOTRON_NANO,
    "QAManager":                NEMOTRON_NANO,
    "SecurityManager":          NEMOTRON_SUPER,       # Security needs strong reasoning
    "DevOpsManager":            NEMOTRON_NANO,
    "ReliabilityManager":       NEMOTRON_NANO,

    # Level 3 — Planning Workers
    "RequirementAgent":         NEMOTRON_SUPER,       # High quality requirements
    "RiskAnalyzer":             NEMOTRON_SUPER,       # Deep risk evaluation

    # Level 3 — Engineering Workers (Fast code generation)
    "BackendAgent":             LLAMA_VISION,         # Sub-second code generation
    "APIAgent":                 LLAMA_VISION,
    "FrontendAgent":            LLAMA_VISION,
    "ArchitectAgent":           NEMOTRON_SUPER,
    "CoderAgent":               LLAMA_VISION,

    # Level 3 — QA Workers
    "TestAgent":                LLAMA_VISION,         # Fast test suite generation
    "ReviewerAgent":            NEMOTRON_NANO,        # Fast code review
    "RuntimeExecutionAgent":    NEMOTRON_NANO,

    # Level 3 — Security Workers
    "ScannerAgent":             NEMOTRON_SUPER,       # Rigorous security scanning

    # Level 3 — DevOps Workers
    "DeployAgent":              LLAMA_VISION,         # CI/CD and Dockerfiles

    # Level 3 — Reliability Workers
    "DiagnosticsAgent":         NEMOTRON_NANO,        # Fast diagnostics
    "RepairAgent":              LLAMA_VISION,         # Code repair
    "RetryCoordinator":         NEMOTRON_NANO,        # Coordination

    # Level 3 — Cross-cutting & Validation
    "KnowledgeMemoryAgent":     NEMOTRON_NANO,        # Memory summarization
    "HallucinationValidator":   LLAMA_VISION,
    "SemanticValidator":        LLAMA_VISION,
    "ContractValidator":        LLAMA_VISION,
    "HumanApprovalGateway":     NEMOTRON_SUPER,
    "EvaluatorAgent":           NEMOTRON_SUPER,
    "CriticAgent":              NEMOTRON_SUPER,
    "RefinerAgent":             LLAMA_VISION,
    "HallucinationDetectorAgent": NEMOTRON_NANO,
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

def _get_client(provider: Optional[str] = None) -> tuple[AsyncOpenAI, str]:
    """
    Returns (AsyncOpenAI client, effective_provider_name).
    Supports NVIDIA NIM, Google Gemini (OpenAI-compatible endpoint), and Ollama.
    """
    env_provider = provider or os.environ.get("LLM_PROVIDER", "").lower()
    
    if env_provider == "ollama":
        return AsyncOpenAI(
            base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
            api_key="ollama",
        ), "ollama"

    nvidia_key = os.environ.get("NVIDIA_API_KEY", "").strip()
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()

    if env_provider == "gemini":
        if not gemini_key:
            raise EnvironmentError("GEMINI_API_KEY not set for Gemini provider.")
        return AsyncOpenAI(
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            api_key=gemini_key,
        ), "gemini"

    # Default / NVIDIA provider preference
    if nvidia_key:
        return AsyncOpenAI(
            base_url=os.environ.get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
            api_key=nvidia_key,
        ), "nvidia"

    # Fallback to Gemini if NVIDIA key is absent but Gemini key is available
    if gemini_key:
        logger.info("NVIDIA_API_KEY not found; falling back to GEMINI_API_KEY.")
        return AsyncOpenAI(
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            api_key=gemini_key,
        ), "gemini"

    # Neither key found
    raise EnvironmentError(
        "No LLM API keys detected. Please set NVIDIA_API_KEY or GEMINI_API_KEY in environment or Secret Manager."
    )


def get_model_for_agent(agent_name: str) -> str:
    """
    Returns the allotted primary NIM model ID for a given agent.
    Falls back to LLAMA_VISION if agent name is not found.
    """
    provider = os.environ.get("LLM_PROVIDER", "").lower()
    if provider == "ollama":
        return "gemma4:e2b"
    if provider == "gemini":
        return "gemini-2.0-flash"
    model = AGENT_MODEL_MAP.get(agent_name)
    if not model:
        logger.warning(f"No model mapping for '{agent_name}' — defaulting to {LLAMA_VISION}")
        return LLAMA_VISION
    return model


# ─────────────────────────────────────────────────────────────
#  CORE INFERENCE CALL WITH AUTOMATIC MODEL FAILOVER
# ─────────────────────────────────────────────────────────────

def _get_model_timeout(model: str) -> float:
    """Computes a realistic timeout (in seconds) per model to prevent premature aborts."""
    try:
        from config import get_settings
        configured_timeout = float(get_settings().agent_timeout_seconds)
    except Exception:
        configured_timeout = 90.0

    env_timeout = os.environ.get("LLM_TIMEOUT_SECONDS")
    if env_timeout:
        try:
            return float(env_timeout)
        except ValueError:
            pass

    # Large 120B / deep reasoning models get full configured budget (min 60s)
    if "120b" in model.lower() or "pro" in model.lower():
        return max(configured_timeout, 60.0)
    
    # Fast models (11B / flash / nano) get 45s
    return max(min(configured_timeout, 45.0), 30.0)


async def call_agent_llm(
    agent_name: str,
    prompt: str,
    system: Optional[str] = None,
    max_tokens: int = 2048,
    temperature: float = 0.2,
    task_id: Optional[str] = None,
) -> str:
    """
    Main inference function. Queries the Model Router for candidate fallback
    models and automatically switches to alternative models if the primary
    model times out, returns HTTP 404/429/500/503, or is deprecated.
    Also seamlessly fails over to Gemini if NVIDIA NIM times out or is unavailable.
    """
    task_type = AGENT_TO_TASK_TYPE.get(agent_name, "default")
    
    # ── LLM Guardrail Check: Input
    guard_in = check_and_sanitize_input(prompt)
    if not guard_in.is_safe:
        logger.error(f"[{agent_name}] LLM Input Guardrail blocked request: {guard_in.reason}")
        raise ValueError(guard_in.reason)

    safe_prompt = sanitize_llm_input(guard_in.content)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": safe_prompt})

    # Obtain primary client & provider
    client, provider = _get_client()

    if provider == "ollama":
        candidates = [("gemma4:e2b", "ollama")]
    elif provider == "gemini":
        candidates = [("gemini-2.0-flash", "gemini"), ("gemini-1.5-pro", "gemini")]
    else:
        from engines.model_router import get_candidate_models_for_task, select_optimal_model
        primary_optimal = await select_optimal_model(task_type)
        task_candidates = get_candidate_models_for_task(task_type)
        
        # Build candidate chain: primary first, followed by others without duplicates
        raw_candidates = [primary_optimal]
        agent_allotted = AGENT_MODEL_MAP.get(agent_name)
        if agent_allotted and agent_allotted not in raw_candidates:
            raw_candidates.append(agent_allotted)
        for m in task_candidates:
            if m not in raw_candidates:
                raw_candidates.append(m)

        candidates = [(m, "nvidia") for m in raw_candidates]

        # Add Google Gemini as emergency cloud failover if GEMINI_API_KEY exists
        if os.environ.get("GEMINI_API_KEY"):
            candidates.append(("gemini-2.0-flash", "gemini"))

    last_error: Optional[Exception] = None

    # ── Attempt models in candidate fallback chain
    for attempt_idx, (model, model_provider) in enumerate(candidates):
        logger.info(f"[{agent_name}] Attempt {attempt_idx + 1}/{len(candidates)} using {model_provider} model: {model}")
        start_time = time.time()
        success = False

        # Switch client if this candidate uses a different provider (e.g. Gemini failover)
        active_client = client
        if model_provider != provider:
            try:
                active_client, _ = _get_client(provider=model_provider)
            except Exception as ce:
                logger.warning(f"Could not initialize provider client for {model_provider}: {ce}")
                continue

        timeout_sec = _get_model_timeout(model)

        try:
            response = await active_client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=timeout_sec,
            )
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Received empty response from model")
                
            success = True
            prompt_tokens = response.usage.prompt_tokens if (response.usage and hasattr(response.usage, "prompt_tokens")) else 0
            completion_tokens = response.usage.completion_tokens if (response.usage and hasattr(response.usage, "completion_tokens")) else 0
            tokens_used = response.usage.total_tokens if (response.usage and hasattr(response.usage, "total_tokens")) else 0
            
            logger.info(f"[{agent_name}] Model {model} responded successfully ({tokens_used} tokens)")

            # Record token usage for budget tracking
            if tokens_used:
                record_token_usage("system", int(tokens_used))

            # Record task-level cost/token billing
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

            # Guardrail Output Check
            guard_out = check_and_sanitize_output(content)
            if "Hallucination Warning" in guard_out.reason:
                logger.warning(f"[{agent_name}] LLM Output Guardrail warning: {guard_out.reason}")

            return sanitize_llm_output(guard_out.content)

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000.0
            last_error = e
            logger.warning(f"[{agent_name}] Model {model} ({model_provider}) failed after {latency_ms:.0f}ms: {e}. Switching to fallback model...")
            if model_provider != "ollama":
                try:
                    from engines.model_router import log_model_outcome
                    await log_model_outcome(model, task_type, latency_ms, False)
                except Exception:
                    pass
            continue
        finally:
            if success and model_provider != "ollama":
                latency_ms = (time.time() - start_time) * 1000.0
                try:
                    from engines.model_router import log_model_outcome
                    await log_model_outcome(model, task_type, latency_ms, True)
                except Exception:
                    pass

    # If all candidate models in the chain failed
    logger.error(f"[{agent_name}] All {len(candidates)} candidate models failed. Last error: {last_error}")
    raise last_error or RuntimeError(f"All LLM models failed for agent {agent_name}")


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
#  MODEL REGISTRY (used by /agents endpoint)
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
