"""
model_router.py — Intelligent Model Selection Engine
Selects optimal LLM dynamically based on task type, requirements, and performance.
"""

import logging
from typing import Dict, Any, List, Optional
from memory.db_client import get_db_session, ModelPerformanceDB

logger = logging.getLogger(__name__)

# Verified model IDs matching llm_factory.py
MODEL_REGISTRY = {
    "qwen/qwen3-coder-480b-a35b-instruct": {
        "model_id": "qwen/qwen3-coder-480b-a35b-instruct",
        "strengths": ["coding", "debugging", "refactoring"],
        "task_types": ["code_generation", "bug_fix", "refactoring", "testing"],
        "latency_ms": 1200,
        "cost_per_1k_tokens": 0.0005,
        "context_window": 128000,
        "provider": "nvidia_nim"
    },
    "meta/llama-3.3-70b-instruct": {
        "model_id": "meta/llama-3.3-70b-instruct",
        "strengths": ["reasoning", "planning", "analysis", "security"],
        "task_types": ["architecture", "task_decomposition", "planning", "security_scan"],
        "latency_ms": 1800,
        "cost_per_1k_tokens": 0.0007,
        "context_window": 128000,
        "provider": "nvidia_nim"
    },
    "meta/llama-4-maverick-17b-128e-instruct": {
        "model_id": "meta/llama-4-maverick-17b-128e-instruct",
        "strengths": ["general", "validation", "planning"],
        "task_types": ["validation", "planning", "diagnostics"],
        "latency_ms": 900,
        "cost_per_1k_tokens": 0.0002,
        "context_window": 128000,
        "provider": "nvidia_nim"
    },
    "meta/llama-3.1-8b-instruct": {
        "model_id": "meta/llama-3.1-8b-instruct",
        "strengths": ["fast", "lightweight", "coordination"],
        "task_types": ["coordination", "summarization", "validation"],
        "latency_ms": 400,
        "cost_per_1k_tokens": 0.0001,
        "context_window": 128000,
        "provider": "nvidia_nim"
    },
    "deepseek-ai/deepseek-v4-flash": {
        "model_id": "deepseek-ai/deepseek-v4-flash",
        "strengths": ["fast", "agentic", "diagnostics"],
        "task_types": ["diagnostics", "coordination", "reliability"],
        "latency_ms": 300,
        "cost_per_1k_tokens": 0.00008,
        "context_window": 64000,
        "provider": "nvidia_nim"
    }
}

DEFAULT_MODELS = {
    "code_generation": "qwen/qwen3-coder-480b-a35b-instruct",
    "bug_fix": "qwen/qwen3-coder-480b-a35b-instruct",
    "refactoring": "qwen/qwen3-coder-480b-a35b-instruct",
    "testing": "qwen/qwen3-coder-480b-a35b-instruct",
    "architecture": "meta/llama-3.3-70b-instruct",
    "task_decomposition": "meta/llama-3.3-70b-instruct",
    "planning": "meta/llama-4-maverick-17b-128e-instruct",
    "security_scan": "meta/llama-3.3-70b-instruct",
    "validation": "meta/llama-4-maverick-17b-128e-instruct",
    "diagnostics": "deepseek-ai/deepseek-v4-flash",
    "coordination": "meta/llama-3.1-8b-instruct",
    "reliability": "deepseek-ai/deepseek-v4-flash",
    "default": "deepseek-ai/deepseek-v4-flash"
}


async def select_optimal_model(task_type: str, requirements: Optional[Dict[str, Any]] = None) -> str:
    """
    Intelligently select the best model for a given task type and requirements.
    
    Args:
        task_type: Category of work (coding, reasoning, testing, etc.)
        requirements: Optional dictionary containing constraints like:
            - max_latency_ms (int)
            - max_cost_per_token (float)
            - min_context_window (int)
            - min_success_rate (float)
            
    Returns:
        The optimal model ID string.
    """
    requirements = requirements or {}
    
    # 1. Filter models by task_type compatibility (fallback to default mappings if no custom types matched)
    compatible_models = [
        meta for model_id, meta in MODEL_REGISTRY.items()
        if task_type in meta["task_types"]
    ]
    
    if not compatible_models:
        # If task type doesn't match any registered category, check if it maps to generic categories
        # E.g., if agent requests a role we map to default
        fallback_model = DEFAULT_MODELS.get(task_type, DEFAULT_MODELS["default"])
        logger.info(f"No direct model category match for task_type '{task_type}'. Falling back to default: {fallback_model}")
        return fallback_model

    # 2. Apply requirement filters (latency, cost, context window)
    filtered = []
    for model in compatible_models:
        model_id = model["model_id"]
        
        # Max latency constraint
        if "max_latency_ms" in requirements and model["latency_ms"] > requirements["max_latency_ms"]:
            continue
            
        # Max cost constraint
        if "max_cost_per_token" in requirements and model["cost_per_1k_tokens"] / 1000.0 > requirements["max_cost_per_token"]:
            continue
            
        # Min context window constraint
        if "min_context_window" in requirements and model["context_window"] < requirements["min_context_window"]:
            continue
            
        filtered.append(model)
        
    if not filtered:
        # If requirements were too strict, log warning and fallback to all compatible models
        logger.warning(f"No models satisfied requirements {requirements} for task_type '{task_type}'. Ignoring constraints.")
        filtered = compatible_models

    # 3. Score models using database historical performance if available
    scored_models = []
    async for session in get_db_session():
        db_perf = ModelPerformanceDB(session) if session else None
        
        for model in filtered:
            model_id = model["model_id"]
            
            # Fetch performance metrics
            success_rate = 100.0
            avg_latency = float(model["latency_ms"])
            
            if db_perf:
                try:
                    perf = await db_perf.get_performance(model_id, task_type)
                    if perf:
                        success_rate = perf.get("success_rate", 100.0)
                        avg_latency = perf.get("avg_latency_ms", avg_latency)
                except Exception as e:
                    logger.warning(f"Failed to query model performance for {model_id}: {e}")
            
            # Scoring formula: higher success rate and lower latency is better
            # Score success rate (0-100) highly, and penalize high latency
            # success_rate * 0.8 + (10000.0 / (avg_latency + 1.0)) * 0.2
            score = (success_rate * 0.8) + (10000.0 / (avg_latency + 100.0)) * 0.2
            
            # Apply user constraints on success rate if specified
            if "min_success_rate" in requirements and success_rate < requirements["min_success_rate"]:
                score -= 1000.0  # Heavy penalty for violating user threshold
                
            scored_models.append((model_id, score))
        break
    else:
        # In case async generator did not yield, fall back to registry defaults
        for model in filtered:
            score = 100.0 - (model["latency_ms"] / 10.0)
            scored_models.append((model["model_id"], score))

    if not scored_models:
        fallback = DEFAULT_MODELS.get(task_type, DEFAULT_MODELS["default"])
        logger.warning(f"No scored models for task_type '{task_type}'. Returning fallback: {fallback}")
        return fallback

    # Select highest scoring model
    scored_models.sort(key=lambda x: x[1], reverse=True)
    selected_model = scored_models[0][0]
    logger.info(f"Model Router selected '{selected_model}' for task_type '{task_type}' (Score: {scored_models[0][1]:.2f})")
    return selected_model


async def log_model_outcome(model_name: str, task_type: str, latency_ms: float, success: bool):
    """
    Log performance metrics for a model invocation.
    """
    model_meta = MODEL_REGISTRY.get(model_name, {})
    cost_per_token = (model_meta.get("cost_per_1k_tokens", 0.0) / 1000.0) if model_meta else 0.0
    
    async for session in get_db_session():
        if not session:
            # Running in mock mode
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