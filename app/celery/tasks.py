# app/celery/tasks.py

import base64
import time
import numpy as np
import cv2
from io import BytesIO
from PIL import Image
import os

from .config import celery_app
from .notify import publish_status


@celery_app.task(bind=True)
def binarize_image_task(self, img_bytes: bytes, algorithm: str, user_id: int):
    task_id = self.request.id

    # Старт
    publish_status(user_id, {
        "status": "STARTED",
        "task_id": task_id,
        "algorithm": algorithm
    })

    try:
        # Загрузка изображения
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)

        if img is None:
            raise ValueError("Не удалось открыть изображение")

        # Прогресс 1
        publish_status(user_id, {"status": "PROGRESS", "task_id": task_id, "progress": 20})
        time.sleep(0.5)

        # Бинаризация
        if algorithm == "otsu":
            _, bin_img = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        elif algorithm == "adaptive":
            bin_img = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                            cv2.THRESH_BINARY, 11, 2)
        elif algorithm == "custom":
            avg = np.mean(img)
            _, bin_img = cv2.threshold(img, avg, 255, cv2.THRESH_BINARY)
        else:
            raise ValueError(f"Неизвестный алгоритм: {algorithm}")

        # Прогресс 2
        publish_status(user_id, {"status": "PROGRESS", "task_id": task_id, "progress": 80})
        time.sleep(0.5)

        # Сохранение результата в байты
        _, encoded_img = cv2.imencode(".png", bin_img)

        # ✅ Сохранение файла на диск
        os.makedirs("results", exist_ok=True)  # Создаём папку, если её нет
        file_path = f"results/{task_id}.png"
        with open(file_path, "wb") as f:
            f.write(encoded_img.tobytes())  # Сохраняем бинарные данные

        # Base64-кодирование (по-прежнему нужно для WebSocket)
        bin_img_b64 = base64.b64encode(encoded_img.tobytes()).decode()

        # Отправка завершения
        publish_status(user_id, {
            "status": "COMPLETED",
            "task_id": task_id,
            "file_path": file_path,  # Путь к файлу в ответе
            "binarized_image": bin_img_b64
        })

        return {"file_path": file_path, "binarized_image": bin_img_b64}

    except Exception as e:
        publish_status(user_id, {
            "status": "FAILED",
            "task_id": task_id,
            "error": str(e)
        })
        raise