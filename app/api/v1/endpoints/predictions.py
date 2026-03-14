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
import numpy as np

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

    # --- ส่วนที่ 1: แปลง Array เป็น Varchar (Text) ---
    try:
        age_text = encoder.age_categories[np.argmax(predictions_dict["age_result"])]
        gender_text = encoder.gender_categories[
            np.argmax(predictions_dict["gender_result"])
        ]

        if sum(predictions_dict["hairstyle_result"]) == 0:
            hairstyle_text = "ศีรษะล้าน"
            haircolor_text = "ไม่ระบุ"
        else:
            hairstyle_text = encoder.hair_style_categories[
                np.argmax(predictions_dict["hairstyle_result"])
            ]
            haircolor_text = encoder.hair_color_categories[
                np.argmax(predictions_dict["haircolor_result"])
            ]

        skin_text = encoder.skin_categories[np.argmax(predictions_dict["skin_result"])]

        # Multi-label
        eyebrow_texts = [
            cat
            for i, cat in enumerate(encoder.eyebrow_categories)
            if predictions_dict["eyebrows_result"][i] == 1
        ]
        eyebrow_string = ", ".join(eyebrow_texts) or "ไม่ระบุ"

        beard_texts = [
            cat
            for i, cat in enumerate(encoder.beard_categories)
            if predictions_dict["beard_result"][i] == 1
        ]
        beard_string = ", ".join(beard_texts) or "ไม่มีหนวดเครา"
    except (KeyError, IndexError) as e:
        raise HTTPException(
            status_code=400, detail=f"ข้อมูล Array ที่ส่งมาไม่ครบหรือไม่ถูกต้อง: {str(e)}"
        )
    # ----------------------------------------------

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

    # --- ส่วนที่ 2: ส่งค่า String เข้า Schema ---
    prediction_data = prediction_schema.PredictionCreate(
        image_filename=new_file_name,
        image_url=image_url,
        age_result=age_text,
        gender_result=gender_text,
        haircolor_result=haircolor_text,
        hairstyle_result=hairstyle_text,
        eyebrows_result=eyebrow_string,
        skin_result=skin_text,
        beard_result=beard_string,
    )

    saved_prediction = await prediction_crud.create_prediction(
        db=db, prediction_data=prediction_data, user_id=current_user.id
    )

    return saved_prediction
