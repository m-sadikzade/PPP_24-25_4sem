import asyncio, json, redis
from fastapi import APIRouter, WebSocket, Query
from app.websocket.manager import manager
from app.core.auth import verify_jwt

ws_router = APIRouter(tags=["websocket"])

@ws_router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket, token: str = Query(...)):
    """Личный канал пользователя по JWT-токену (?token=)."""
    user = verify_jwt(token)
    if not user:
        await ws.close(code=1008)
        return

    user_id = str(user["id"])
    await manager.connect(user_id, ws)

    r = redis.Redis(host="localhost", port=6379, db=0)
    pubsub = r.pubsub()
    pubsub.subscribe(f"user_{user_id}_channel")

    try:
        while True:
            msg = pubsub.get_message(ignore_subscribe_messages=True, timeout=1)
            if msg and isinstance(msg["data"], bytes):
                data = json.loads(msg["data"])
                await manager.send(user_id, data)
            await asyncio.sleep(0.25)
    finally:
        manager.disconnect(user_id)
        pubsub.close()
