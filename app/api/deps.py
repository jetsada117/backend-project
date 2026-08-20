from typing import AsyncGenerator
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.user import User
from app.schemas.token import TokenPayload
from app.crud import user as user_crud

reusable_oauth2 = OAuth2PasswordBearer(tokenUrl=f"/api/v1/auth/login")


async def get_db() -> AsyncGenerator:
    """
    สร้าง Database Session และปิดอัตโนมัติหลังใช้งาน
    """
    async with SessionLocal() as db:
        try:
            yield db
        finally:
            pass


async def get_current_user(
    db: AsyncSession = Depends(get_db), token: str = Depends(reusable_oauth2)
) -> User:
    """
    ตรวจสอบ JWT Token และดึงข้อมูลผู้ใช้ปัจจุบัน
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="สิทธิ์การเข้าถึงไม่ถูกต้อง หรือโทเค็นหมดอายุ",
        )
    user = await user_crud.get_user_by_id(db, user_id=int(token_data.sub))
    if not user:
        raise HTTPException(status_code=404, detail="ไม่พบข้อมูลผู้ใช้งานในระบบ")
    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    ดึงข้อมูลผู้ใช้ที่ Login อยู่และ Active
    """
    return current_user
