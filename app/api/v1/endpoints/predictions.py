import os
import uuid
import json
import logging
import time

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.user import User
from app.services.storage_service import storage_service
from app.services.prediction_service import predictor_service
from app.services.encoding_service import encoder
from app.crud import predictions as prediction_crud
from app.schemas import predictions as prediction_schema
import numpy as np

logger = logging.getLogger("uvicorn")
router = APIRouter()


@router.post("/")
async def predict_item_image(
    file: UploadFile = File(...),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    รับรูปภาพและรัน ML Models เพื่อทำนายลักษณะใบหน้าทั้งหมด
    """
    MAX_FILE_SIZE = 5 * 1024 * 1024
    if file.size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="ขนาดไฟล์ต้องไม่เกิน 5MB")

    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="ไฟล์ต้องเป็นรูปภาพเท่านั้น")

    contents = await file.read()

    ml_start_time = time.perf_counter()
    try:
        predictions = await predictor_service.predict_all(contents)
    except Exception as e:
        import traceback

        print(traceback.format_exc())
        raise HTTPException(
            status_code=500, detail=f"เกิดข้อผิดพลาดในการทำนายผล: {str(e)}"
        )
    ml_elapsed_time = time.perf_counter() - ml_start_time
    logger.info(
        f"User ID: {current_user.id} | ML Model Predictions finished | "
        f"Taken: {ml_elapsed_time:.4f}s"
    )

    full_vector = encoder.combine_results_to_vector(predictions)
    descriptions = encoder.vector_to_text(full_vector)

    return {
        "message": "ทำนายผลสำเร็จ กรุณาตรวจสอบและยืนยันเพื่อบันทึก",
        "features": predictions,
        "descriptions": descriptions,
    }


@router.post("/save", response_model=prediction_schema.Prediction)
async def save_item_prediction(
    file: UploadFile = File(...),
    predictions_json: str = Form(..., description="ข้อมูลผลการทำนาย (JSON string)"),
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    อัปโหลดรูปภาพและบันทึกผลการทำนายที่ผู้ใช้ยืนยันแล้วลงฐานข้อมูล
    """
    try:
        predictions_dict = json.loads(predictions_json)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400, detail="รูปแบบข้อมูล JSON ของผลทำนายไม่ถูกต้อง"
        )

    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="ไฟล์ต้องเป็นรูปภาพเท่านั้น")

    MAX_FILE_SIZE = 5 * 1024 * 1024
    if file.size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="ขนาดไฟล์ต้องไม่เกิน 5MB")

    try:
        thai_desc = encoder.get_thai_description_dict(predictions_dict)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    contents = await file.read()
    file_extension = os.path.splitext(file.filename)[1]
    new_file_name = f"{uuid.uuid4()}{file_extension}"

    try:
        image_url = await storage_service.upload_file(
            file_content=contents,
            file_name=new_file_name,
            content_type=file.content_type,
            folder="predictions",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"เกิดข้อผิดพลาดในการอัปโหลดรูปภาพ: {str(e)}"
        )

    full_vector = encoder.combine_results_to_vector(predictions_dict)
    full_vector_list = [int(x) for x in full_vector]

    prediction_data = prediction_schema.PredictionCreate(
        image_filename=new_file_name,
        image_url=image_url,
        age_result=thai_desc["age"],
        gender_result=thai_desc["gender"],
        haircolor_result=thai_desc["haircolor"],
        hairstyle_result=thai_desc["hairstyle"],
        eyebrows_result=thai_desc["eyebrows"],
        skin_result=thai_desc["skin"],
        beard_result=thai_desc["beard"],
        prediction_vector=full_vector_list,
    )

    saved_prediction = await prediction_crud.create_prediction(
        db=db, prediction_data=prediction_data, user_id=current_user.id
    )

    return saved_prediction
