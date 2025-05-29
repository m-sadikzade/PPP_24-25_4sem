from fastapi import FastAPI
from app.api import tasks, websocket

app = FastAPI(title="FastAPI Binarization Service", version="0.1.0")

app.include_router(tasks.router)
app.include_router(websocket.ws_router)
