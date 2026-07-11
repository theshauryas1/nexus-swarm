import pytest
from engines.memory_engine import generate_embedding, get_pseudo_embedding, MemoryEngine

def test_pseudo_embedding_properties():
    # 1. Output is list of float
    emb1 = get_pseudo_embedding("implement user authentication using JWT tokens")
    assert isinstance(emb1, list)
    assert len(emb1) == 1024
    assert all(isinstance(x, float) for x in emb1)

    # 2. Check normalization (sum of squares ≈ 1.0)
    sq_sum = sum(x*x for x in emb1)
    assert abs(sq_sum - 1.0) < 1e-5

    # 3. Check deterministic output
    emb2 = get_pseudo_embedding("implement user authentication using JWT tokens")
    assert emb1 == emb2

    # 4. Check keyword overlap similarity
    emb_diff = get_pseudo_embedding("completely different topic about database indexes")
    dot_same = sum(a*b for a, b in zip(emb1, emb2))
    dot_diff = sum(a*b for a, b in zip(emb1, emb_diff))
    assert dot_same > dot_diff

@pytest.mark.asyncio
async def test_add_and_search_memories():
    # Force mock mode in tests to isolate test execution from live DB connections
    import memory.db_client
    memory.db_client._use_mock_db = True

    # Clear mock memories first (since we run in mock mode in tests)
    from memory.db_client import _MOCK_MEMORIES
    _MOCK_MEMORIES.clear()

    # Save some memories
    mem1_id = await MemoryEngine.add_memory(
        content="JWT tokens should be stored in HTTP-only cookies to prevent XSS attacks.",
        memory_type="security_standard"
    )
    mem2_id = await MemoryEngine.add_memory(
        content="Use raw SQL queries with parameterized variables to block SQL injection.",
        memory_type="coding_standard"
    )

    assert mem1_id is not None
    assert mem2_id is not None
    assert len(_MOCK_MEMORIES) == 2

    # Search memories
    results = await MemoryEngine.semantic_search("XSS attacks and JWT token storage", limit=1)
    assert len(results) == 1
    assert "JWT tokens" in results[0]["content"]
    assert results[0]["similarity"] > 0.1
    # Check access count was incremented
    assert results[0]["access_count"] == 1
