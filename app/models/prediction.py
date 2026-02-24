from sqlalchemy import Column, Integer, String, ForeignKey, JSON
from sqlalchemy.orm import relationship
from .base_class import Base


class Predictions(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    image_filename = Column(String(255), unique=True, index=True, nullable=False)
    image_url = Column(String(500), nullable=False)

    age_result = Column(JSON)
    gender_result = Column(JSON)
    haircolor_result = Column(JSON)
    hairstyle_result = Column(JSON)
    eyebrows_result = Column(JSON)
    skin_result = Column(JSON)
    beard_result = Column(JSON)

    user_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="predictions")
