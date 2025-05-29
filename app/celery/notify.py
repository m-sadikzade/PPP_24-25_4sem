# app/celery/notify.py
import json
import redis

def publish_status(user_id: int | str, message: dict) -> None:
    """Отправляет JSON-строку в Redis-канал пользователя."""
    r = redis.Redis(host="localhost", port=6379, db=0)
    r.publish(f"user_{user_id}_channel", json.dumps(message))