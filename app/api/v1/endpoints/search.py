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
    current_user_vector = encoder.text_to_vector(description)

    db_predictions = await prediction_crud.get_prediction(db)

    results = []
    for item in db_predictions:
        db_vector = (
            item.age_result
            + item.gender_result
            + item.haircolor_result
            + item.hairstyle_result
            + item.eyebrows_result
            + item.skin_result
            + item.beard_result
        )

        score = scorer.calculate_similarity(current_user_vector, db_vector)

        thai_features_list = encoder.vector_to_text(db_vector)

        results.append(
            {
                "id": item.prediction_id,
                "image_url": item.image_url,
                "similarity_score": round(score * 100, 2),
                "features": thai_features_list,
            }
        )

    results.sort(key=lambda x: x["similarity_score"], reverse=True)

    return results[:limit]
