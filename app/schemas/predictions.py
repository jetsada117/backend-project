from typing import Optional, List, Any, Dict
from pydantic import BaseModel


class PredictionFeatures(BaseModel):
    age_result: Optional[List[Any]] = None
    gender_result: Optional[List[Any]] = None
    haircolor_result: Optional[List[Any]] = None
    hairstyle_result: Optional[List[Any]] = None
    eyebrows_result: Optional[List[Any]] = None
    skin_result: Optional[List[Any]] = None
    beard_result: Optional[List[Any]] = None

    @property
    def feature_vector(self) -> List[float]:
        """
        ดึงข้อมูลแต่ละ Label มาต่อกันเป็น List เดียว (ความยาว 25 มิติ)
        ใช้ or [] เพื่อป้องกัน Error ในกรณีที่ข้อมูลใน DB บางฟิลด์มีค่าเป็น None
        """
        return (
            (self.age_result or [])
            + (self.gender_result or [])
            + (self.haircolor_result or [])
            + (self.hairstyle_result or [])
            + (self.eyebrows_result or [])
            + (self.skin_result or [])
            + (self.beard_result or [])
        )


class PredictionBase(PredictionFeatures):
    image_filename: str
    image_url: str


class PredictionCreate(PredictionBase):
    pass


class Prediction(PredictionBase):
    id: int


class PredictResponse(BaseModel):
    message: str
    features: PredictionFeatures
    descriptions: Dict[str, str]
