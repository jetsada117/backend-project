import os
import uuid
import json

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.user import User
from app.services.storage_service import storage_service
from app.services.prediction_service import predictor_service
from app.services.encoding_service import encoder
from app.crud import predictions as prediction_crud
from app.schemas import predictions as prediction_schema

router = APIRouter()


@router.post("/")
async def predict_item_image(
    file: UploadFile = File(...),
    current_user: User = Depends(deps.get_current_active_user),
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="ไฟล์ต้องเป็นรูปภาพเท่านั้น")

    contents = await file.read()

    try:
        predictions = await predictor_service.predict_all(contents)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"เกิดข้อผิดพลาดในการทำนายผล: {str(e)}"
        )

    full_vector = (
        (predictions.get("age_result") or [])
        + (predictions.get("gender_result") or [])
        + (predictions.get("haircolor_result") or [])
        + (predictions.get("hairstyle_result") or [])
        + (predictions.get("eyebrows_result") or [])
        + (predictions.get("skin_result") or [])
        + (predictions.get("beard_result") or [])
    )
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
    try:
        predictions_dict = json.loads(predictions_json)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="รูปแบบข้อมูล JSON ของผลทำนายไม่ถูกต้อง")

    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="ไฟล์ต้องเป็นรูปภาพเท่านั้น")

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

    prediction_data = prediction_schema.PredictionCreate(
        image_filename=new_file_name,
        image_url=image_url,
        **predictions_dict,
    )

    saved_prediction = await prediction_crud.create_prediction(
        db=db, prediction_data=prediction_data, user_id=current_user.id
    )

    return saved_prediction
