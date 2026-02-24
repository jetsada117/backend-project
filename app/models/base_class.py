from sqlalchemy.orm import DeclarativeBase


# สร้าง Base Class ก่อน เพื่อให้ทุก Model สืบทอดมาจากตัวนี้
class Base(DeclarativeBase):
    pass
