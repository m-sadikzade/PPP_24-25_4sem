# Лабораторная №3. Asynchronous API: Celery + WebSocket + Redis

## Запуск

```bash
pip install -r requirements.txt           # зависимости

redis-server                     

python -m celery -A app.celery.tasks.celery_app worker --loglevel=info --pool=solo
python -m uvicorn main:app --reload

python client.py