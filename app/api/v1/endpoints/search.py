from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud import predictions as prediction_crud
from app.models.user import User
from app.services.encoding_service import encoder
from app.services.cosine_similarity_service import scorer

from app.api import deps

router = APIRouter()


@router.get("")
async def calculate_similarity(
    description: str = Query(..., description="คำบรรยายลักษณะใบหน้า"),
    limit: int = Query(4, ge=1, le=6, description="จำนวนผลลัพธ์สูงสุดที่ต้องการแสดง"),
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    # 1. แปลง Input Text เป็น Vector (NumPy Array)
    current_user_vector = encoder.text_to_vector(description)

    # 2. ดึงข้อมูลจาก DB
    db_predictions = await prediction_crud.get_prediction(db)

    if not db_predictions:
        return []

    # 3. เตรียม Matrix จากข้อมูลใน DB
    valid_items = []
    vectors_list = []

    for item in db_predictions:
        # ใช้ Vector ที่บันทึกไว้ใน DB หากมี (Optimization)
        if item.prediction_vector:
            db_vector = item.prediction_vector
        else:
            # Fallback สำหรับข้อมูลเก่าที่ยังไม่มี vector ใน DB
            db_text_features = (
                f"{item.age_result or ''} "
                f"{item.gender_result or ''} "
                f"{item.haircolor_result or ''} "
                f"{item.hairstyle_result or ''} "
                f"{item.eyebrows_result or ''} "
                f"{item.skin_result or ''} "
                f"{item.beard_result or ''}"
            ).strip()
            db_vector = encoder.text_to_vector(db_text_features).tolist()

        if len(db_vector) == len(scorer.expanded_weights):
            valid_items.append(item)
            vectors_list.append(db_vector)

    if not vectors_list:
        return []

    # แปลงเป็น NumPy Matrix (N, 25)
    import numpy as np

    db_matrix = np.array(vectors_list)

    # 4. คำนวณ Similarity ทุกแถวพร้อมกันด้วย NumPy Matrix Operations
    scores = scorer.calculate_similarity_matrix(current_user_vector, db_matrix)

    # 5. รวบรวมผลลัพธ์
    results = []
    for i, item in enumerate(valid_items):
        # เตรียมข้อมูล features สำหรับแสดงผล (อิงจากผลลัพธ์ที่เป็นข้อความ)
        db_text_features_for_display = (
            f"{item.age_result or ''} "
            f"{item.gender_result or ''} "
            f"{item.haircolor_result or ''} "
            f"{item.hairstyle_result or ''} "
            f"{item.eyebrows_result or ''} "
            f"{item.skin_result or ''} "
            f"{item.beard_result or ''}"
        ).strip()

        thai_features_list = [
            feature.strip()
            for feature in db_text_features_for_display.replace(",", " ").split()
            if feature.strip()
        ]

        results.append(
            {
                "id": item.prediction_id,
                "image_url": item.image_url,
                "similarity_score": round(float(scores[i]) * 100, 2),
                "features": thai_features_list,
            }
        )

    # 6. เรียงลำดับและคืนค่า
    results.sort(key=lambda x: x["similarity_score"], reverse=True)

    return results[:limit]
