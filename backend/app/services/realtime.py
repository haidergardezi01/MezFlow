import json
import logging
from decimal import Decimal
from typing import Dict, Set
from uuid import UUID
import redis.asyncio as aioredis
from fastapi import WebSocket

from app.core.config import settings

logger = logging.getLogger("mezflow.realtime")


class MezFlowJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, Decimal):
            return float(obj)
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
        payload_str = json.dumps(message, cls=MezFlowJsonEncoder)

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
        await self.broadcast_to_local(rest_id_str, event_data)

        try:
            r = self.get_redis()
            channel = f"channel:menu:{rest_id_str}"
            payload_str = json.dumps(event_data, cls=MezFlowJsonEncoder)
            await r.publish(channel, payload_str)
        except Exception as e:
            logger.error(f"Failed to publish event to Redis: {e}")


class SessionConnectionManager:
    """Manages collaborative table sessions over WebSockets and Redis Pub/Sub."""

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

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        if session_id not in self._active_connections:
            self._active_connections[session_id] = set()
        self._active_connections[session_id].add(websocket)
        logger.info(f"WebSocket connected for table session {session_id}. Total: {len(self._active_connections[session_id])}")

    def disconnect(self, session_id: str, websocket: WebSocket):
        if session_id in self._active_connections:
            self._active_connections[session_id].discard(websocket)
            if not self._active_connections[session_id]:
                del self._active_connections[session_id]
        logger.info(f"WebSocket disconnected for table session {session_id}")

    async def broadcast_to_local(self, session_id: str, message: dict):
        if session_id not in self._active_connections:
            return

        dead_connections = set()
        payload_str = json.dumps(message, cls=MezFlowJsonEncoder)

        for ws in self._active_connections[session_id]:
            try:
                await ws.send_text(payload_str)
            except Exception as e:
                logger.warning(f"Error sending session update to websocket: {e}")
                dead_connections.add(ws)

        for ws in dead_connections:
            self._active_connections[session_id].discard(ws)

    async def publish_event(self, session_id: UUID | str, event_data: dict):
        """Dispatches event locally and publishes to Redis PubSub for all session participants."""
        sess_id_str = str(session_id)
        await self.broadcast_to_local(sess_id_str, event_data)

        try:
            r = self.get_redis()
            channel = f"channel:session:{sess_id_str}"
            payload_str = json.dumps(event_data, cls=MezFlowJsonEncoder)
            await r.publish(channel, payload_str)
        except Exception as e:
            logger.error(f"Failed to publish session event to Redis: {e}")

    async def publish_kds_order(self, restaurant_id: UUID | str, order_data: dict):
        """Dispatches order event to Kitchen Display System (M4 KDS bridge)."""
        await kds_connection_manager.publish_event(restaurant_id, order_data)


class KDSConnectionManager:
    """Manages active WebSockets and Redis Pub/Sub for Kitchen Display System (KDS)."""

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
        logger.info(f"WebSocket connected for KDS restaurant {restaurant_id}. Total: {len(self._active_connections[restaurant_id])}")

    def disconnect(self, restaurant_id: str, websocket: WebSocket):
        if restaurant_id in self._active_connections:
            self._active_connections[restaurant_id].discard(websocket)
            if not self._active_connections[restaurant_id]:
                del self._active_connections[restaurant_id]
        logger.info(f"WebSocket disconnected for KDS restaurant {restaurant_id}")

    async def broadcast_to_local(self, restaurant_id: str, message: dict):
        if restaurant_id not in self._active_connections:
            return

        dead_connections = set()
        payload_str = json.dumps(message, cls=MezFlowJsonEncoder)

        for ws in self._active_connections[restaurant_id]:
            try:
                await ws.send_text(payload_str)
            except Exception as e:
                logger.warning(f"Error sending KDS update to websocket: {e}")
                dead_connections.add(ws)

        for ws in dead_connections:
            self._active_connections[restaurant_id].discard(ws)

    async def publish_event(self, restaurant_id: UUID | str, event_data: dict):
        """Dispatches event locally and publishes to Redis Pub/Sub for all KDS screens."""
        rest_id_str = str(restaurant_id)
        await self.broadcast_to_local(rest_id_str, event_data)

        try:
            r = self.get_redis()
            channel = f"channel:kds:{rest_id_str}"
            payload_str = json.dumps(event_data, cls=MezFlowJsonEncoder)
            await r.publish(channel, payload_str)
            logger.info(f"Dispatched KDS event {event_data.get('event')} to {channel}")
        except Exception as e:
            logger.error(f"Failed to publish KDS event to Redis: {e}")


menu_connection_manager = MenuConnectionManager()
session_connection_manager = SessionConnectionManager()
kds_connection_manager = KDSConnectionManager()

