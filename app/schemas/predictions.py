from typing import Optional, List, Any
from pydantic import BaseModel


class PredictionBase(BaseModel):
    image_filename: str
    image_url: str

    age_result: Optional[List[Any]] = None
    gender_result: Optional[List[Any]] = None
    haircolor_result: Optional[List[Any]] = None
    hairstyle_result: Optional[List[Any]] = None
    eyebrows_result: Optional[List[Any]] = None
    skin_result: Optional[List[Any]] = None
    beard_result: Optional[List[Any]] = None


class PredictionCreate(PredictionBase):
    pass


class Prediction(PredictionBase):
    id: int
    user_id: int
