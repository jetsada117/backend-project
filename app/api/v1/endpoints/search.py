from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud import predictions as prediction_crud
from app.services.encoding_service import encoder
from app.services.cosine_similarity_service import scorer

from app.api import deps

router = APIRouter()


@router.get("/")
async def calculate_similarity(
    description: str = Query(..., description="คำบรรยายลักษณะใบหน้า"),
    db: AsyncSession = Depends(deps.get_db),
):
    current_user_vector = encoder.text_to_vector(description)
    db_predictions = await prediction_crud.get_prediction(db)

    results = []
    for item in db_predictions:
        db_vector = item.feature_vector

        score = scorer.calculate_similarity(current_user_vector, db_vector)

        results.append(
            {
                "id": item.id,
                "image_url": item.image_url,
                "similarity_score": round(score * 100, 2),
            }
        )

    results.sort(key=lambda x: x["similarity_score"], reverse=True)

    return results[:5]
