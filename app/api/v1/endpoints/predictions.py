from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.api import deps
from app.models.user import User
from app.services.storage_service import storage_service
from app.services.prediction_service import predictor_service
from app.crud import predictions as prediction_crud

from app.schemas import predictions as prediction_schema


import os
import uuid

router = APIRouter()


@router.post("/", response_model=prediction_schema.Prediction)
async def upload_item_image(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="ไฟล์ต้องเป็นรูปภาพเท่านั้น")

    file_extension = os.path.splitext(file.filename)[1]
    new_file_name = f"{uuid.uuid4()}{file_extension}"

    contents = await file.read()

    try:
        predictions = await predictor_service.predict_all(contents)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"เกิดข้อผิดพลาดในการทำนายผล: {str(e)}"
        )

    image_url = await storage_service.upload_file(
        file_content=contents,
        file_name=new_file_name,
        content_type=file.content_type,
        folder="predictions",
    )

    prediction_data = prediction_schema.PredictionCreate(
        image_filename=new_file_name,
        image_url=image_url,
        **predictions,
    )

    saved_prediction = await prediction_crud.create_prediction(
        db=db, prediction_data=prediction_data, user_id=1
    )

    return saved_prediction
