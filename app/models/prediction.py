from sqlalchemy import Column, Integer, String, ForeignKey, JSON
from .base_class import Base


class Prediction(Base):
    __tablename__ = "predictions"

    prediction_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    image_filename = Column(String(255), unique=True, index=True)
    image_url = Column(String(512), nullable=False)

    age_result = Column(String(50), nullable=False)
    gender_result = Column(String(50), nullable=False)
    haircolor_result = Column(String(50), nullable=False)
    hairstyle_result = Column(String(50), nullable=False)
    eyebrows_result = Column(String(50), nullable=False)
    skin_result = Column(String(50), nullable=False)
    beard_result = Column(String(50), nullable=False)

    prediction_vector = Column(JSON, nullable=True)

    user_id = Column(Integer, ForeignKey("users.id"))
