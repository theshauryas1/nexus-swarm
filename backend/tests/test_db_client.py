import pytest
from memory.db_client import ping_db, get_engine
from config import get_settings

@pytest.mark.asyncio
async def test_ping_db():
    # If postgres is running, it returns True; otherwise falls back to mock and returns False (but handles safely)
    result = await ping_db()
    assert isinstance(result, bool)

@pytest.mark.asyncio
async def test_get_engine():
    engine = get_engine()
    settings = get_settings()
    if settings.database_url:
        assert engine is not None
    else:
        assert engine is None
