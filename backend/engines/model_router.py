"""
model_router.py — Intelligent Model Selection & Dynamic Fallback Engine
Selects optimal LLMs dynamically with automatic multi-model fallback chains.
"""

import logging
from typing import Dict, Any, List, Optional
from memory.db_client import get_db_session, ModelPerformanceDB

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
#  LIVE VERIFIED MODEL REGISTRY (NVIDIA NIM 2026)
# ─────────────────────────────────────────────────────────────
MODEL_REGISTRY = {
    "meta/llama-3.2-11b-vision-instruct": {
        "model_id": "meta/llama-3.2-11b-vision-instruct",
        "strengths": ["coding", "debugging", "refactoring", "testing", "fast_inference"],
        "task_types": ["code_generation", "bug_fix", "refactoring", "testing", "validation", "coordination"],
        "latency_ms": 600,
        "cost_per_1k_tokens": 0.0001,
        "context_window": 128000,
        "provider": "nvidia_nim"
    },
    "nvidia/nemotron-3-super-120b-a12b": {
        "model_id": "nvidia/nemotron-3-super-120b-a12b",
        "strengths": ["reasoning", "planning", "analysis", "security", "architecture", "orchestration"],
        "task_types": ["architecture", "task_decomposition", "planning", "security_scan", "code_generation"],
        "latency_ms": 1500,
        "cost_per_1k_tokens": 0.0008,
        "context_window": 128000,
        "provider": "nvidia_nim"
    },
    "nvidia/nemotron-3-nano-30b-a3b": {
        "model_id": "nvidia/nemotron-3-nano-30b-a3b",
        "strengths": ["fast", "lightweight", "coordination", "diagnostics", "summarization"],
        "task_types": ["coordination", "summarization", "validation", "diagnostics", "reliability", "planning"],
        "latency_ms": 380,
        "cost_per_1k_tokens": 0.00008,
        "context_window": 64000,
        "provider": "nvidia_nim"
    },
    "nvidia/nemotron-3.5-lightning-30b-a3b": {
        "model_id": "nvidia/nemotron-3.5-lightning-30b-a3b",
        "strengths": ["deep_reasoning", "refactoring", "code_generation"],
        "task_types": ["refactoring", "code_generation", "planning", "validation"],
        "latency_ms": 2500,
        "cost_per_1k_tokens": 0.0002,
        "context_window": 128000,
        "provider": "nvidia_nim"
    },
    "deepseek-ai/deepseek-v4-pro-0813": {
        "model_id": "deepseek-ai/deepseek-v4-pro-0813",
        "strengths": ["agentic", "diagnostics", "reliability", "reasoning"],
        "task_types": ["diagnostics", "reliability", "coordination", "validation"],
        "latency_ms": 2000,
        "cost_per_1k_tokens": 0.0002,
        "context_window": 128000,
        "provider": "nvidia_nim"
    },
    "gemini-2.0-flash": {
        "model_id": "gemini-2.0-flash",
        "strengths": ["speed", "multimodal", "reasoning", "coding", "low_latency"],
        "task_types": ["task_decomposition", "planning", "code_generation", "bug_fix", "refactoring", "testing", "coordination", "security_scan"],
        "latency_ms": 450,
        "cost_per_1k_tokens": 0.0001,
        "context_window": 1000000,
        "provider": "google_gemini"
    },
    "gemini-1.5-pro": {
        "model_id": "gemini-1.5-pro",
        "strengths": ["deep_reasoning", "architecture", "security", "long_context"],
        "task_types": ["architecture", "task_decomposition", "planning", "security_scan", "refactoring"],
        "latency_ms": 1200,
        "cost_per_1k_tokens": 0.00125,
        "context_window": 2000000,
        "provider": "google_gemini"
    }
}

# Ordered Fallback Chains by Domain
TASK_FALLBACK_CHAINS: Dict[str, List[str]] = {
    # High-reasoning & security domain
    "architecture": [
        "nvidia/nemotron-3-super-120b-a12b",
        "nvidia/nemotron-3.5-lightning-30b-a3b",
        "meta/llama-3.2-11b-vision-instruct",
    ],
    "task_decomposition": [
        "nvidia/nemotron-3-super-120b-a12b",
        "nvidia/nemotron-3.5-lightning-30b-a3b",
        "meta/llama-3.2-11b-vision-instruct",
    ],
    "security_scan": [
        "nvidia/nemotron-3-super-120b-a12b",
        "nvidia/nemotron-3.5-lightning-30b-a3b",
        "meta/llama-3.2-11b-vision-instruct",
    ],
    "planning": [
        "nvidia/nemotron-3-super-120b-a12b",
        "nvidia/nemotron-3-nano-30b-a3b",
        "meta/llama-3.2-11b-vision-instruct",
    ],

    # Code generation & testing domain
    "code_generation": [
        "meta/llama-3.2-11b-vision-instruct",
        "nvidia/nemotron-3.5-lightning-30b-a3b",
        "nvidia/nemotron-3-super-120b-a12b",
        "nvidia/nemotron-3-nano-30b-a3b",
    ],
    "bug_fix": [
        "meta/llama-3.2-11b-vision-instruct",
        "nvidia/nemotron-3.5-lightning-30b-a3b",
        "nvidia/nemotron-3-nano-30b-a3b",
    ],
    "refactoring": [
        "meta/llama-3.2-11b-vision-instruct",
        "nvidia/nemotron-3.5-lightning-30b-a3b",
        "nvidia/nemotron-3-nano-30b-a3b",
    ],
    "testing": [
        "meta/llama-3.2-11b-vision-instruct",
        "nvidia/nemotron-3.5-lightning-30b-a3b",
        "nvidia/nemotron-3-nano-30b-a3b",
    ],

    # Coordination & management domain
    "coordination": [
        "nvidia/nemotron-3-nano-30b-a3b",
        "meta/llama-3.2-11b-vision-instruct",
        "deepseek-ai/deepseek-v4-pro-0813",
    ],
    "summarization": [
        "nvidia/nemotron-3-nano-30b-a3b",
        "meta/llama-3.2-11b-vision-instruct",
    ],

    # Diagnostics, validation & reliability domain
    "diagnostics": [
        "nvidia/nemotron-3-nano-30b-a3b",
        "deepseek-ai/deepseek-v4-pro-0813",
        "meta/llama-3.2-11b-vision-instruct",
    ],
    "validation": [
        "meta/llama-3.2-11b-vision-instruct",
        "nvidia/nemotron-3-nano-30b-a3b",
        "deepseek-ai/deepseek-v4-pro-0813",
    ],
    "reliability": [
        "nvidia/nemotron-3-nano-30b-a3b",
        "deepseek-ai/deepseek-v4-pro-0813",
        "meta/llama-3.2-11b-vision-instruct",
    ],
    "default": [
        "meta/llama-3.2-11b-vision-instruct",
        "nvidia/nemotron-3-nano-30b-a3b",
        "nvidia/nemotron-3-super-120b-a12b",
    ]
}

DEFAULT_MODELS = {
    "code_generation": "meta/llama-3.2-11b-vision-instruct",
    "bug_fix": "meta/llama-3.2-11b-vision-instruct",
    "refactoring": "meta/llama-3.2-11b-vision-instruct",
    "testing": "meta/llama-3.2-11b-vision-instruct",
    "architecture": "nvidia/nemotron-3-super-120b-a12b",
    "task_decomposition": "nvidia/nemotron-3-super-120b-a12b",
    "planning": "nvidia/nemotron-3-super-120b-a12b",
    "security_scan": "nvidia/nemotron-3-super-120b-a12b",
    "validation": "meta/llama-3.2-11b-vision-instruct",
    "diagnostics": "nvidia/nemotron-3-nano-30b-a3b",
    "coordination": "nvidia/nemotron-3-nano-30b-a3b",
    "reliability": "nvidia/nemotron-3-nano-30b-a3b",
    "default": "meta/llama-3.2-11b-vision-instruct"
}


def get_candidate_models_for_task(task_type: str) -> List[str]:
    """Returns the ordered list of fallback models for a given task type."""
    return TASK_FALLBACK_CHAINS.get(task_type, TASK_FALLBACK_CHAINS["default"])


async def select_optimal_model(task_type: str, requirements: Optional[Dict[str, Any]] = None) -> str:
    """
    Intelligently select the best model for a given task type and requirements.
    """
    requirements = requirements or {}
    candidates = get_candidate_models_for_task(task_type)
    
    if not candidates:
        return DEFAULT_MODELS.get(task_type, DEFAULT_MODELS["default"])

    # If requirements specify constraints, filter candidates
    filtered = []
    for model_id in candidates:
        model = MODEL_REGISTRY.get(model_id)
        if not model:
            continue
            
        if "max_latency_ms" in requirements and model["latency_ms"] > requirements["max_latency_ms"]:
            continue
            
        if "max_cost_per_token" in requirements and (model["cost_per_1k_tokens"] / 1000.0) > requirements["max_cost_per_token"]:
            continue
            
        if "min_context_window" in requirements and model["context_window"] < requirements["min_context_window"]:
            continue
            
        filtered.append(model_id)
        
    if not filtered:
        # Constraints too strict, use default candidate list
        filtered = candidates

    # Query historical performance for ranking
    scored_models = []
    async for session in get_db_session():
        db_perf = ModelPerformanceDB(session) if session else None
        
        for idx, model_id in enumerate(filtered):
            model = MODEL_REGISTRY.get(model_id, {})
            success_rate = 100.0
            avg_latency = float(model.get("latency_ms", 1000))
            
            # Base priority score based on candidate order (primary candidate gets highest base)
            base_priority = (len(filtered) - idx) * 100.0
            
            if db_perf:
                try:
                    perf = await db_perf.get_performance(model_id, task_type)
                    if perf:
                        success_rate = perf.get("success_rate", 100.0)
                        avg_latency = perf.get("avg_latency_ms", avg_latency)
                except Exception as e:
                    logger.warning(f"Failed to query model performance for {model_id}: {e}")
            
            score = base_priority + (success_rate * 0.8) + (10000.0 / (avg_latency + 100.0)) * 0.2
            if "min_success_rate" in requirements and success_rate < requirements["min_success_rate"]:
                score -= 1000.0
                
            scored_models.append((model_id, score))
        break
    else:
        for idx, model_id in enumerate(filtered):
            base_priority = (len(filtered) - idx) * 100.0
            scored_models.append((model_id, base_priority))

    if scored_models:
        scored_models.sort(key=lambda x: x[1], reverse=True)
        return scored_models[0][0]

    return candidates[0]


async def log_model_outcome(model_name: str, task_type: str, latency_ms: float, success: bool):
    """
    Log performance metrics for a model invocation.
    """
    model_meta = MODEL_REGISTRY.get(model_name, {})
    cost_per_token = (model_meta.get("cost_per_1k_tokens", 0.0) / 1000.0) if model_meta else 0.0
    
    async for session in get_db_session():
        if not session:
            from memory.db_client import ModelPerformanceDB as MockDB
            db = MockDB(None)
            await db.log_performance(model_name, task_type, latency_ms, success, cost_per_token)
            break
            
        db = ModelPerformanceDB(session)
        try:
            await db.log_performance(model_name, task_type, latency_ms, success, cost_per_token)
        except Exception as e:
            logger.error(f"Error logging model performance to DB: {e}")
        break