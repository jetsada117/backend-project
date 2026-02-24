from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import json

from app.schemas.predictions import Prediction, PredictionCreate


async def create_prediction(
    db: AsyncSession, prediction_data: PredictionCreate, user_id: int
):
    sql = text(
        """
        INSERT INTO predictions (
            image_filename, image_url, age_result, gender_result, 
            haircolor_result, hairstyle_result, eyebrows_result, 
            skin_result, beard_result, user_id
        ) 
        VALUES (
            :image_filename, :image_url, :age_result, :gender_result, 
            :haircolor_result, :hairstyle_result, :eyebrows_result, 
            :skin_result, :beard_result, :user_id
        )
    """
    )

    data_dict = prediction_data.model_dump()

    params = {
        "image_filename": data_dict["image_filename"],
        "image_url": data_dict["image_url"],
        "age_result": json.dumps(data_dict["age_result"]),
        "gender_result": json.dumps(data_dict["gender_result"]),
        "haircolor_result": json.dumps(data_dict["haircolor_result"]),
        "hairstyle_result": json.dumps(data_dict["hairstyle_result"]),
        "eyebrows_result": json.dumps(data_dict["eyebrows_result"]),
        "skin_result": json.dumps(data_dict["skin_result"]),
        "beard_result": json.dumps(data_dict["beard_result"]),
        "user_id": user_id,
    }

    result = await db.execute(sql, params)
    await db.commit()

    inserted_id = result.lastrowid

    return {"id": inserted_id, "user_id": user_id, **data_dict}
