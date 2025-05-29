import base64
import time
from .config import celery_app
from .notify import publish_status


@celery_app.task(bind=True)
def binarize_image_task(self, img_bytes: bytes, algorithm: str, user_id: int):
    """
    Эмуляция длительной бинаризации.
    Алгоритм передаётся, чтобы в будущем выбрать OpenCV/Pillow метод.
    """
    task_id = self.request.id

    # Старт
    publish_status(user_id, {
        "status": "STARTED",
        "task_id": task_id,
        "algorithm": algorithm
    })

    # Прогресс
    steps = 5
    for i in range(1, steps + 1):
        time.sleep(1)
        publish_status(user_id, {
            "status": "PROGRESS",
            "task_id": task_id,
            "progress": int(i / steps * 100)
        })

    # TODO: здесь реальная бинаризация изображения
    bin_img_b64 = base64.b64encode(img_bytes).decode()

    # Завершение
    publish_status(user_id, {
        "status": "COMPLETED",
        "task_id": task_id,
        "binarized_image": bin_img_b64
    })
    return {"binarized_image": bin_img_b64}
