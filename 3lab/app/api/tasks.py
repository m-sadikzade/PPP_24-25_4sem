# app/api/tasks.py
from fastapi import APIRouter, File, UploadFile, Form, Depends
from app.celery.tasks import binarize_image_task
from app.core.auth import get_current_user

router = APIRouter(tags=["image"])

@router.post("/binarize/", summary="Upload image and start binarization")
async def upload_image(
    file: UploadFile = File(..., description="Изображение"),
    algorithm: str = Form(..., description="Алгоритм (otsu, adaptive …)"),
    user: dict = Depends(get_current_user), 
):
    img_bytes = await file.read()
    task = binarize_image_task.apply_async(
        args=[img_bytes, algorithm, user["id"]]
    )
    return {"task_id": task.id}