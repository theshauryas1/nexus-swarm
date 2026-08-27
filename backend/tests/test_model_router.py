import pytest
import asyncio
from engines.model_router import (
    select_optimal_model,
    log_model_outcome,
    get_candidate_models_for_task,
    MODEL_REGISTRY,
    TASK_FALLBACK_CHAINS
)

@pytest.mark.asyncio
async def test_select_optimal_model_coding():
    # meta/llama-3.2-11b-vision-instruct should be primary for code_generation
    model = await select_optimal_model("code_generation")
    assert model == "meta/llama-3.2-11b-vision-instruct"

@pytest.mark.asyncio
async def test_select_optimal_model_reasoning():
    # nvidia/nemotron-3-super-120b-a12b should be selected for task_decomposition
    model = await select_optimal_model("task_decomposition")
    assert model == "nvidia/nemotron-3-super-120b-a12b"

@pytest.mark.asyncio
async def test_candidate_models_fallback_chain():
    # Verify fallback chains contain valid registered models
    coding_chain = get_candidate_models_for_task("code_generation")
    assert len(coding_chain) >= 2
    assert "meta/llama-3.2-11b-vision-instruct" in coding_chain
    for m in coding_chain:
        assert m in MODEL_REGISTRY

@pytest.mark.asyncio
async def test_select_optimal_model_with_latency_constraint():
    # Requesting with low latency constraint selects fastest compatible model
    requirements = {"max_latency_ms": 700}
    model = await select_optimal_model("code_generation", requirements)
    assert model in MODEL_REGISTRY
    assert MODEL_REGISTRY[model]["latency_ms"] <= 700

@pytest.mark.asyncio
async def test_log_model_outcome():
    # Log performance results and verify no exceptions are thrown
    await log_model_outcome("meta/llama-3.2-11b-vision-instruct", "code_generation", 550.0, True)
    await log_model_outcome("nvidia/nemotron-3-super-120b-a12b", "task_decomposition", 1200.0, True)
