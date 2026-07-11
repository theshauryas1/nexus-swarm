"""
memory_engine.py — Long-Term Memory Engine
Handles memory storage, retrieval, and semantic embeddings via NVIDIA NIM.
"""

import logging
import hashlib
import math
from typing import List, Optional, Dict, Any
from openai import AsyncOpenAI
import os

from memory.db_client import get_db_session, MemoryDB
from config import get_settings

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "nvidia/embed-qa-4"
EMBEDDING_DIM = 1024


def get_pseudo_embedding(text: str, dimensions: int = EMBEDDING_DIM) -> List[float]:
    """
    Generate a deterministic, normalized pseudo-embedding based on word hashing.
    Used as a fallback when the NVIDIA embedding API fails or is not configured.
    Provides basic similarity ranking based on keyword overlap.
    """
    vec = [0.0] * dimensions
    # Simple tokenization
    import re
    words = re.findall(r'[a-zA-Z0-9_]+', text.lower())
    if not words:
        return vec
        
    for word in words:
        # Generate multiple indices per word to distribute weight (min-hash inspired)
        h = int(hashlib.md5(word.encode('utf-8')).hexdigest(), 16)
        for i in range(5):
            idx = (h + i * 101) % dimensions
            # Weight based on hash bits
            val = ((h >> (i * 8)) & 0xFF) / 255.0
            vec[idx] += val
            
    # L2 Normalization
    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 0:
        vec = [x / norm for x in vec]
    return vec


async def generate_embedding(text: str) -> List[float]:
    """
    Generate vector embedding using NVIDIA NIM embedding models.
    Falls back to deterministic pseudo-embedding on error or if credentials are missing.
    """
    settings = get_settings()
    api_key = os.environ.get("NVIDIA_API_KEY") or settings.nvidia_api_key
    
    if not api_key:
        logger.warning("NVIDIA_API_KEY is not set. Generating pseudo-embedding for memory.")
        return get_pseudo_embedding(text)

    try:
        # Use AsyncOpenAI client configured for NVIDIA NIM
        client = AsyncOpenAI(
            base_url=settings.nvidia_base_url,
            api_key=api_key,
        )
        
        logger.info(f"Generating semantic embedding via NVIDIA NIM: {EMBEDDING_MODEL}")
        response = await client.embeddings.create(
            input=[text],
            model=EMBEDDING_MODEL
        )
        
        embedding = response.data[0].embedding
        if len(embedding) == EMBEDDING_DIM:
            return embedding
        else:
            logger.warning(f"Unexpected embedding dimension: {len(embedding)} (expected {EMBEDDING_DIM}). Generating pseudo-embedding.")
            return get_pseudo_embedding(text)
            
    except Exception as e:
        logger.error(f"NVIDIA Embedding API call failed: {e}. Falling back to pseudo-embedding.")
        return get_pseudo_embedding(text)


class MemoryEngine:
    """
    High-level manager for storing and querying swarm memories.
    """
    
    @staticmethod
    async def add_memory(
        content: str,
        memory_type: str,
        task_id: Optional[str] = None,
        confidence_score: float = 1.0
    ) -> str:
        """
        Record a new long-term memory. Automatically generates semantic embedding.
        """
        logger.info(f"Adding memory type '{memory_type}': '{content[:60]}...'")
        embedding = await generate_embedding(content)
        
        async for session in get_db_session():
            if not session:
                # Mock DB path
                from memory.db_client import MemoryDB as MockDB
                db = MockDB(None)
                memory_id = await db.save_memory(content, memory_type, embedding, task_id, confidence_score)
                return memory_id
                
            db = MemoryDB(session)
            try:
                memory_id = await db.save_memory(content, memory_type, embedding, task_id, confidence_score)
                return memory_id
            except Exception as e:
                logger.error(f"Error saving memory to DB: {e}")
                # Try fallback saving without embedding or in mock storage
                from memory.db_client import MemoryDB as MockDB
                db = MockDB(None)
                return await db.save_memory(content, memory_type, embedding, task_id, confidence_score)


    @staticmethod
    async def semantic_search(query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Find related memories using cosine similarity against the query string.
        """
        logger.info(f"Searching memory for query: '{query}'")
        query_embedding = await generate_embedding(query)
        
        async for session in get_db_session():
            if not session:
                # Mock DB path
                from memory.db_client import MemoryDB as MockDB
                db = MockDB(None)
                return await db.semantic_search(query_embedding, limit)
                
            db = MemoryDB(session)
            try:
                return await db.semantic_search(query_embedding, limit)
            except Exception as e:
                logger.error(f"Error searching memories in DB: {e}")
                # Fallback to mock retrieval
                from memory.db_client import MemoryDB as MockDB
                db = MockDB(None)
                return await db.semantic_search(query_embedding, limit)
        return []
