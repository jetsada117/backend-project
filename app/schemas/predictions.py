from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class RawPredictionFeatures(BaseModel):
    age_result: Optional[List[int]] = None
    gender_result: Optional[List[int]] = None
    haircolor_result: Optional[List[int]] = None
    hairstyle_result: Optional[List[int]] = None
    eyebrows_result: Optional[List[int]] = None
    skin_result: Optional[List[int]] = None
    beard_result: Optional[List[int]] = None


class PredictResponse(BaseModel):
    message: str
    features: RawPredictionFeatures
    descriptions: List[str]


class PredictionBase(BaseModel):
    image_filename: str
    image_url: str


class PredictionCreate(PredictionBase):
    age_result: str
    gender_result: str
    haircolor_result: str
    hairstyle_result: str
    eyebrows_result: str
    skin_result: str
    beard_result: str
    prediction_vector: List[int]


class Prediction(PredictionBase):
    prediction_id: int
    user_id: Optional[int] = None

    age_result: str
    gender_result: str
    haircolor_result: str
    hairstyle_result: str
    eyebrows_result: str
    skin_result: str
    beard_result: str
    prediction_vector: Optional[List[int]] = None
