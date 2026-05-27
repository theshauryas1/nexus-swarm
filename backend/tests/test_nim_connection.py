import pytest
import os
from agents.llm_factory import call_agent_llm

@pytest.mark.asyncio
@pytest.mark.skipif(
    os.environ.get("RUN_NIM_INTEGRATION_TESTS") != "1" or not os.environ.get("NVIDIA_API_KEY"),
    reason="Live NIM integration test requires RUN_NIM_INTEGRATION_TESTS=1 and NVIDIA_API_KEY.",
)
async def test_real_nim_call():
    """Confirms NVIDIA NIM API key is valid and model responds."""
    result = await call_agent_llm(
        agent_name="HeadOrchestrator",
        prompt="Reply with exactly: NIM_CONNECTION_OK",
        system="You are a test agent. Follow instructions exactly."
    )
    assert result is not None
    assert len(result) > 0
    print(f"\nNIM Response: {result[:100]}")
