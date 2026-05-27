"""
NexusSwarm — Redis Client
Pipeline state, pub/sub bus, inter-manager communication
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator, Callable

import redis.asyncio as aioredis

from config import get_settings

logger = logging.getLogger(__name__)

# ─── Redis channel names ─────────────────────────────────────────
CHANNEL_AGENT_EVENTS  = "nexusswarm:agent_events"
CHANNEL_PIPELINE_HEALTH = "nexusswarm:pipeline_health"
CHANNEL_CONFLICTS     = "nexusswarm:conflicts"

# ─── Redis key patterns ──────────────────────────────────────────
KEY_TASK_STATE        = "nexusswarm:task:{task_id}:state"
KEY_PIPELINE_STATE    = "nexusswarm:task:{task_id}:pipeline:{pipeline}"
KEY_AGENT_STATUS      = "nexusswarm:agent:{agent_name}:status"
KEY_ACTIVE_TASKS      = "nexusswarm:active_tasks"


class RedisClient:
    """
    Async Redis client wrapping pub/sub and key/value operations.
    Singleton — use get_redis() to access.
    """

    def __init__(self, url: str):
        self._url = url
        self._client: aioredis.Redis | None = None
        self._pubsub: aioredis.client.PubSub | None = None

    async def connect(self) -> None:
        self._client = aioredis.from_url(
            self._url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
        )
        await self._client.ping()
        logger.info("✅ Redis connected at %s", self._url)

    async def disconnect(self) -> None:
        if self._pubsub:
            await self._pubsub.close()
        if self._client:
            await self._client.aclose()
        logger.info("Redis disconnected")

    async def ping(self) -> bool:
        try:
            return await self._client.ping()
        except Exception:
            return False

    # ── Pub/Sub ────────────────────────────────────────────────────

    async def publish(self, channel: str, message: dict) -> None:
        """Publish a JSON message to a Redis channel."""
        payload = json.dumps(message, default=str)
        await self._client.publish(channel, payload)

    async def publish_agent_event(self, event: dict) -> None:
        await self.publish(CHANNEL_AGENT_EVENTS, event)

    async def publish_health_event(self, event: dict) -> None:
        await self.publish(CHANNEL_PIPELINE_HEALTH, event)

    async def publish_conflict(self, conflict: dict) -> None:
        await self.publish(CHANNEL_CONFLICTS, conflict)

    @asynccontextmanager
    async def subscribe(self, *channels: str) -> AsyncIterator[aioredis.client.PubSub]:
        """Context manager that yields a PubSub subscriber."""
        pubsub = self._client.pubsub()
        await pubsub.subscribe(*channels)
        try:
            yield pubsub
        finally:
            await pubsub.unsubscribe(*channels)
            await pubsub.close()

    async def listen_to_agent_events(
        self,
        callback: Callable[[dict], asyncio.Future],
    ) -> None:
        """
        Subscribe to all agent event channels and call callback for each message.
        Runs until cancelled.
        """
        channels = [CHANNEL_AGENT_EVENTS, CHANNEL_PIPELINE_HEALTH, CHANNEL_CONFLICTS]
        async with self.subscribe(*channels) as pubsub:
            async for raw_msg in pubsub.listen():
                if raw_msg["type"] != "message":
                    continue
                try:
                    data = json.loads(raw_msg["data"])
                    await callback(data)
                except Exception as e:
                    logger.warning("Error processing Redis message: %s", e)

    # ── Key/Value — Task & Pipeline State ──────────────────────────

    async def set_task_state(self, task_id: str, state: dict, ttl: int = 86400) -> None:
        key = KEY_TASK_STATE.format(task_id=task_id)
        await self._client.setex(key, ttl, json.dumps(state, default=str))

    async def get_task_state(self, task_id: str) -> dict | None:
        key = KEY_TASK_STATE.format(task_id=task_id)
        raw = await self._client.get(key)
        return json.loads(raw) if raw else None

    async def set_pipeline_state(
        self, task_id: str, pipeline: str, state: dict, ttl: int = 86400
    ) -> None:
        key = KEY_PIPELINE_STATE.format(task_id=task_id, pipeline=pipeline)
        await self._client.setex(key, ttl, json.dumps(state, default=str))

    async def get_pipeline_state(self, task_id: str, pipeline: str) -> dict | None:
        key = KEY_PIPELINE_STATE.format(task_id=task_id, pipeline=pipeline)
        raw = await self._client.get(key)
        return json.loads(raw) if raw else None

    # ── Agent Status ───────────────────────────────────────────────

    async def set_agent_status(
        self, agent_name: str, status: str, task_id: str | None = None
    ) -> None:
        key = KEY_AGENT_STATUS.format(agent_name=agent_name)
        await self._client.hset(key, mapping={"status": status, "task_id": task_id or ""})
        await self._client.expire(key, 3600)

    async def get_agent_status(self, agent_name: str) -> dict:
        key = KEY_AGENT_STATUS.format(agent_name=agent_name)
        data = await self._client.hgetall(key)
        return data or {"status": "idle", "task_id": ""}

    # ── Active Tasks Set ───────────────────────────────────────────

    async def add_active_task(self, task_id: str) -> None:
        await self._client.sadd(KEY_ACTIVE_TASKS, task_id)

    async def remove_active_task(self, task_id: str) -> None:
        await self._client.srem(KEY_ACTIVE_TASKS, task_id)

    async def get_active_tasks(self) -> set[str]:
        return await self._client.smembers(KEY_ACTIVE_TASKS)


# ─── Singleton instance ───────────────────────────────────────────
_redis_client = None


class MockPubSub:
    """In-memory PubSub subscriber simulation."""
    def __init__(self, client):
        self.client = client
        self.queue = asyncio.Queue()

    async def listen(self):
        while True:
            msg = await self.queue.get()
            yield {
                "type": "message",
                "data": json.dumps(msg, default=str)
            }


class MockRedisClient:
    """In-memory Redis client fallback."""
    def __init__(self):
        self._url = "mock://localhost:6379"
        self._tasks = {}
        self._pipelines = {}
        self._agents = {}
        self._active_tasks = set()
        self._subscribers = []

    async def connect(self) -> None:
        logger.info("✅ In-Memory Mock Redis connected")

    async def disconnect(self) -> None:
        logger.info("In-Memory Mock Redis disconnected")

    async def ping(self) -> bool:
        return True

    async def publish(self, channel: str, message: dict) -> None:
        # Send to all active subscribers
        for sub in list(self._subscribers):
            await sub.queue.put(message)

    async def publish_agent_event(self, event: dict) -> None:
        await self.publish(CHANNEL_AGENT_EVENTS, event)

    async def publish_health_event(self, event: dict) -> None:
        await self.publish(CHANNEL_PIPELINE_HEALTH, event)

    async def publish_conflict(self, conflict: dict) -> None:
        await self.publish(CHANNEL_CONFLICTS, conflict)

    @asynccontextmanager
    async def subscribe(self, *channels: str) -> AsyncIterator[MockPubSub]:
        sub = MockPubSub(self)
        self._subscribers.append(sub)
        try:
            yield sub
        finally:
            if sub in self._subscribers:
                self._subscribers.remove(sub)

    async def listen_to_agent_events(
        self,
        callback: Callable[[dict], asyncio.Future],
    ) -> None:
        async with self.subscribe() as pubsub:
            async for raw_msg in pubsub.listen():
                if raw_msg["type"] != "message":
                    continue
                try:
                    data = json.loads(raw_msg["data"])
                    await callback(data)
                except Exception as e:
                    logger.warning("Error processing Mock Redis message: %s", e)

    async def set_task_state(self, task_id: str, state: dict, ttl: int = 86400) -> None:
        self._tasks[task_id] = state

    async def get_task_state(self, task_id: str) -> dict | None:
        return self._tasks.get(task_id)

    async def set_pipeline_state(
        self, task_id: str, pipeline: str, state: dict, ttl: int = 86400
    ) -> None:
        self._pipelines[(task_id, pipeline)] = state

    async def get_pipeline_state(self, task_id: str, pipeline: str) -> dict | None:
        return self._pipelines.get((task_id, pipeline))

    async def set_agent_status(
        self, agent_name: str, status: str, task_id: str | None = None
    ) -> None:
        self._agents[agent_name] = {"status": status, "task_id": task_id or ""}

    async def get_agent_status(self, agent_name: str) -> dict:
        return self._agents.get(agent_name, {"status": "idle", "task_id": ""})

    async def add_active_task(self, task_id: str) -> None:
        self._active_tasks.add(task_id)

    async def remove_active_task(self, task_id: str) -> None:
        self._active_tasks.discard(task_id)

    async def get_active_tasks(self) -> set[str]:
        return self._active_tasks


async def get_redis() -> RedisClient:
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        try:
            _redis_client = RedisClient(settings.redis_url)
            await _redis_client.connect()
        except Exception as e:
            logger.warning("⚠️ Real Redis not reachable. Falling back to In-Memory Redis Mock.")
            _redis_client = MockRedisClient()
            await _redis_client.connect()
    return _redis_client


async def close_redis() -> None:
    global _redis_client
    if _redis_client:
        await _redis_client.disconnect()
        _redis_client = None
