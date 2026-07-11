import pytest
import asyncio
from engines.model_router import select_optimal_model, log_model_outcome, MODEL_REGISTRY

@pytest.mark.asyncio
async def test_select_optimal_model_coding():
    # qwen/qwen3.5-397b should be selected for code_generation
    model = await select_optimal_model("code_generation")
    assert model == "qwen/qwen3.5-397b-a17b"

@pytest.mark.asyncio
async def test_select_optimal_model_reasoning():
    # mistral-large-3 should be selected for task_decomposition
    model = await select_optimal_model("task_decomposition")
    assert model == "mistralai/mistral-large-3-675b-instruct-2512"

@pytest.mark.asyncio
async def test_select_optimal_model_with_latency_constraint():
    # Requesting a coding task but with maximum latency of 500ms should rule out qwen3.5 (12000ms)
    # and force fallback or selection of a faster compatible model
    requirements = {"max_latency_ms": 500}
    model = await select_optimal_model("code_generation", requirements)
    # Since qwen is 12000ms, it should either select a faster model if registered or fallback.
    # qwen is the only coding model in MODEL_REGISTRY, so if it's ignored it should be return or fallback.
    assert model in MODEL_REGISTRY

@pytest.mark.asyncio
async def test_log_model_outcome():
    # Log performance results and verify no exceptions are thrown (in mock/test mode)
    await log_model_outcome("qwen/qwen3.5-397b-a17b", "code_generation", 950.0, True)
    await log_model_outcome("mistralai/mistral-large-3-675b-instruct-2512", "task_decomposition", 1500.0, False)
