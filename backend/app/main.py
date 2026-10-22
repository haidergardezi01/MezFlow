import asyncio
import json
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.api import api_router
from app.core.config import settings
from app.services.realtime import menu_connection_manager

logger = logging.getLogger("mezflow.app")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="MezFlow — Real-Time Restaurant Dining and Kitchen Operations Management System API",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Set up CORS (Permissive for local dev ports 3000, 3001, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS or ["http://localhost:3000", "http://localhost:3001"],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API v1 router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Root"])
async def root():
    return {
        "project": settings.PROJECT_NAME,
        "status": "online",
        "docs": "/docs",
        "api_v1": settings.API_V1_STR,
    }


async def _handle_menu_ws(websocket: WebSocket, restaurant_id: str):
    await menu_connection_manager.connect(restaurant_id, websocket)
    try:
        await websocket.send_text(
            json.dumps({
                "event": "CONNECTED",
                "restaurant_id": restaurant_id,
                "message": "Subscribed to live menu availability and price updates",
            })
        )
    except Exception as e:
        logger.warning(f"Could not send init frame: {e}")
        menu_connection_manager.disconnect(restaurant_id, websocket)
        return

    redis = menu_connection_manager.get_redis()
    pubsub = redis.pubsub()
    channel = f"channel:menu:{restaurant_id}"
    try:
        await pubsub.subscribe(channel)
    except Exception as e:
        logger.error(f"Redis subscribe failed: {e}")

    async def redis_listener():
        try:
            async for msg in pubsub.listen():
                if msg and msg.get("type") == "message":
                    payload = msg.get("data")
                    if isinstance(payload, bytes):
                        payload = payload.decode("utf-8")
                    await websocket.send_text(payload)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.debug(f"Redis listener ended: {e}")

    async def client_listener():
        try:
            while True:
                msg = await websocket.receive_text()
                if msg == "ping":
                    await websocket.send_text("pong")
        except (WebSocketDisconnect, asyncio.CancelledError):
            pass
        except Exception as e:
            logger.debug(f"Client listener ended: {e}")

    listener_task = asyncio.create_task(redis_listener())
    client_task = asyncio.create_task(client_listener())

    try:
        done, pending = await asyncio.wait(
            [listener_task, client_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for t in pending:
            t.cancel()
    finally:
        menu_connection_manager.disconnect(restaurant_id, websocket)
        try:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
        except Exception:
            pass


@app.websocket("/ws/restaurants/{restaurant_id}/menu")
async def ws_menu_direct(websocket: WebSocket, restaurant_id: str):
    await _handle_menu_ws(websocket, restaurant_id)


@app.websocket("/api/v1/ws/restaurants/{restaurant_id}/menu")
async def ws_menu_apiv1(websocket: WebSocket, restaurant_id: str):
    await _handle_menu_ws(websocket, restaurant_id)
