# Import Base มาก่อน
from app.models.base_class import Base

# Import Models ทั้งหมดที่อยากให้สร้างตาราง
from app.models.user import User
from app.models.prediction import Prediction

# สรุป: ไฟล์นี้มีหน้าที่รวมญาติ เพื่อให้ Alembic import ไปใช้ที่เดียวจบ
# โดยไม่ต้องไปไล่ import ทีละไฟล์ model
