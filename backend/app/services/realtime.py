import json
import logging
from typing import Dict, Set
from uuid import UUID
import redis.asyncio as aioredis
from fastapi import WebSocket

from app.core.config import settings

logger = logging.getLogger("mezflow.realtime")


class UUIDJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, UUID):
            return str(obj)
        return super().default(obj)


class MenuConnectionManager:
    """Manages active WebSockets and Redis Pub/Sub for real-time menu events."""

    def __init__(self):
        self._active_connections: Dict[str, Set[WebSocket]] = {}
        self._redis_client: aioredis.Redis | None = None

    def get_redis(self) -> aioredis.Redis:
        if self._redis_client is None:
            self._redis_client = aioredis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
            )
        return self._redis_client

    async def connect(self, restaurant_id: str, websocket: WebSocket):
        await websocket.accept()
        if restaurant_id not in self._active_connections:
            self._active_connections[restaurant_id] = set()
        self._active_connections[restaurant_id].add(websocket)
        logger.info(f"WebSocket connected for restaurant {restaurant_id}. Total: {len(self._active_connections[restaurant_id])}")

    def disconnect(self, restaurant_id: str, websocket: WebSocket):
        if restaurant_id in self._active_connections:
            self._active_connections[restaurant_id].discard(websocket)
            if not self._active_connections[restaurant_id]:
                del self._active_connections[restaurant_id]
        logger.info(f"WebSocket disconnected for restaurant {restaurant_id}")

    async def broadcast_to_local(self, restaurant_id: str, message: dict):
        """Immediately dispatch to all local WebSocket connections on this worker."""
        if restaurant_id not in self._active_connections:
            return

        dead_connections = set()
        payload_str = json.dumps(message, cls=UUIDJsonEncoder)

        for ws in self._active_connections[restaurant_id]:
            try:
                await ws.send_text(payload_str)
            except Exception as e:
                logger.warning(f"Error sending to websocket: {e}")
                dead_connections.add(ws)

        for ws in dead_connections:
            self._active_connections[restaurant_id].discard(ws)

    async def publish_event(self, restaurant_id: UUID | str, event_data: dict):
        """Publishes event to Redis PubSub channel and dispatches locally."""
        rest_id_str = str(restaurant_id)
        # 1. Local dispatch for immediate responsiveness (< 10ms)
        await self.broadcast_to_local(rest_id_str, event_data)

        # 2. Redis pub/sub publish for multi-worker / cluster broadcast
        try:
            r = self.get_redis()
            channel = f"channel:menu:{rest_id_str}"
            payload_str = json.dumps(event_data, cls=UUIDJsonEncoder)
            await r.publish(channel, payload_str)
        except Exception as e:
            logger.error(f"Failed to publish event to Redis: {e}")


menu_connection_manager = MenuConnectionManager()
