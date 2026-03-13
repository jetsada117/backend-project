from typing import List

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
        "age_result": data_dict["age_result"],
        "gender_result": data_dict["gender_result"],
        "haircolor_result": data_dict["haircolor_result"],
        "hairstyle_result": data_dict["hairstyle_result"],
        "eyebrows_result": data_dict["eyebrows_result"],
        "skin_result": data_dict["skin_result"],
        "beard_result": data_dict["beard_result"],
        "user_id": user_id,
    }

    result = await db.execute(sql, params)
    await db.commit()

    inserted_id = result.lastrowid

    return {"id": inserted_id, "user_id": user_id, **data_dict}


async def get_prediction(db: AsyncSession) -> List[Prediction]:
    """
    ดึงข้อมูลด้วย Raw SQL และแปลงเป็น Pydantic Schema
    """
    query = text(
        """
        SELECT 
            prediction_id, 
            image_filename, 
            image_url, 
            age_result, 
            gender_result, 
            haircolor_result, 
            hairstyle_result, 
            eyebrows_result, 
            skin_result, 
            beard_result
        FROM predictions
    """
    )

    result = await db.execute(query)
    rows = result.mappings().all()

    predictions_list = []
    for row in rows:
        row_dict = dict(row)

        json_fields = [
            "age_result",
            "gender_result",
            "haircolor_result",
            "hairstyle_result",
            "eyebrows_result",
            "skin_result",
            "beard_result",
        ]

        for field in json_fields:
            if isinstance(row_dict.get(field), str):
                try:
                    row_dict[field] = json.loads(row_dict[field])
                except Exception:
                    row_dict[field] = []

        prediction_model = Prediction(**row_dict)
        predictions_list.append(prediction_model)

    return predictions_list
