"""
cost_tracker.py — NexusSwarm Cost and Token Usage Tracker (LLMOps)
Standalone cost registry to track model token usage and billing metrics per task execution.
Helps answer: "How much did this agent generation run cost?"
"""

import logging
from collections import defaultdict
from contextvars import ContextVar

# ContextVar to track the current task ID in asynchronous tasks
current_task_id: ContextVar[str] = ContextVar("current_task_id", default="")

logger = logging.getLogger(__name__)

# Model input/output token pricing per 1M tokens (verified NVIDIA NIM / OpenAI standard rates)
MODEL_PRICING = {
    # 70B+ / reasoning / code models
    "meta/llama-3.3-70b-instruct": {"input": 0.70, "output": 0.90},
    "mistralai/mistral-large-3-675b-instruct-2512": {"input": 2.00, "output": 6.00},
    "qwen/qwen3.5-397b-a17b": {"input": 1.20, "output": 1.60},
    "qwen/qwen3-next-80b-a3b-instruct": {"input": 1.20, "output": 1.60},
    
    # 8B parameter / lightweight models
    "meta/llama-3.1-8b-instruct": {"input": 0.10, "output": 0.10},
    "meta/llama-4-maverick-17b-128e-instruct": {"input": 0.20, "output": 0.20},
    "deepseek-ai/deepseek-v4-flash": {"input": 0.05, "output": 0.05},
    "gemma4:e2b": {"input": 0.0, "output": 0.0},  # Local Ollama is free
}

# Task ID -> Cost/Token Tracking record
_task_cost_registry = defaultdict(lambda: {
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "total_tokens": 0,
    "estimated_cost": 0.0
})

def calculate_llm_cost(model_id: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Calculate exact USD cost based on prompt and completion token counts."""
    pricing = MODEL_PRICING.get(model_id, {"input": 0.50, "output": 0.50})  # Generic fallback
    input_cost = (prompt_tokens * pricing["input"]) / 1_000_000.0
    output_cost = (completion_tokens * pricing["output"]) / 1_000_000.0
    return input_cost + output_cost

def record_task_llm_usage(task_id: str, model_id: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Record LLM call metrics and update the running aggregates for a task."""
    if not task_id:
        return 0.0
        
    cost = calculate_llm_cost(model_id, prompt_tokens, completion_tokens)
    
    record = _task_cost_registry[task_id]
    record["prompt_tokens"] += prompt_tokens
    record["completion_tokens"] += completion_tokens
    record["total_tokens"] += (prompt_tokens + completion_tokens)
    record["estimated_cost"] += cost
    
    logger.info(
        "[LLMOps] Task %s | Model: %s | Prompt: %d | Compl: %d | Cost: $%.5f | Task Total: %d tokens ($%.5f)",
        task_id[:8] if len(task_id) > 8 else task_id, model_id, prompt_tokens, completion_tokens,
        cost, record["total_tokens"], record["estimated_cost"]
    )
    return cost

def get_task_cost_summary(task_id: str) -> dict:
    """Retrieve the cost/token aggregates accumulated for a task."""
    if not task_id or task_id not in _task_cost_registry:
        return {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "estimated_cost": 0.0
        }
    return dict(_task_cost_registry[task_id])

def clear_task_cost(task_id: str):
    """Clear memory records for a task (after saving to database)."""
    if task_id in _task_cost_registry:
        del _task_cost_registry[task_id]
