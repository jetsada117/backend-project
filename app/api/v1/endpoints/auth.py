from datetime import timedelta
import os
import random
from typing import Any, Optional
import uuid
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Form,
    HTTPException,
    status,
    Request,
    UploadFile,
    File,
)
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.api import deps
from app.core import security
from app.core.config import settings
from app.schemas.auth import LoginRequest
from app.schemas.token import Token, RefreshTokenRequest
from app.schemas.user import UserResponse, UserCreate
from app.crud import user as user_crud
from app.services import email_service, redis_service
from app.services.storage_service import storage_service

router = APIRouter()


@router.post("/login", response_model=Token)
async def login_access_token(
    login_data: LoginRequest,
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    """
    ตรวจสอบ Email และ Password แล้ว Return Access Token และ Refresh Token
    """
    user = await user_crud.authenticate_user(
        db, email=login_data.email, password=login_data.password
    )
    if not user:
        raise HTTPException(status_code=400, detail="อีเมลหรือรหัสผ่านไม่ถูกต้อง")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    return {
        "access_token": security.create_access_token(
            subject=user.id,
            role=user.role,
            expires_delta=access_token_expires,
        ),
        "refresh_token": security.create_refresh_token(user.id),
        "token_type": "bearer",
        "user": user,
    }


@router.post("/request-otp")
async def request_otp(
    email: str = Form(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(deps.get_db),
):
    """
    สร้าง OTP และส่งไปยัง Email ที่ระบุสำหรับการยืนยันตัวตน
    """
    user_exists = await user_crud.get_user_by_email(db, email=email)

    if user_exists:
        raise HTTPException(
            status_code=400,
            detail="อีเมลนี้ถูกใช้งานในระบบแล้ว",
        )

    otp_code = str(random.randint(100000, 999999))
    await redis_service.save_otp(email, otp_code)

    background_tasks.add_task(email_service.send_otp_email, email, otp_code)
    return {"message": "ส่งรหัส OTP ไปยังอีเมลของคุณเรียบร้อยแล้ว"}


@router.post("/register")
async def register_user(
    *,
    db: AsyncSession = Depends(deps.get_db),
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    file: UploadFile = File(...),
    otp_code: str = Form(...),
) -> Any:
    """
    ลงทะเบียนผู้ใช้ใหม่ โดยตรวจสอบ OTP, อัปโหลดรูปโปรไฟล์ และบันทึกข้อมูล
    """
    is_valid = await redis_service.verify_otp(email, otp_code)
    if not is_valid:
        raise HTTPException(status_code=400, detail="รหัส OTP ไม่ถูกต้องหรือหมดอายุ")
    user_exists = await user_crud.get_user_by_email(db, email=email)

    if user_exists:
        raise HTTPException(
            status_code=400,
            detail="อีเมลนี้ถูกใช้งานในระบบแล้ว",
        )

    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="ไฟล์ต้องเป็นรูปภาพเท่านั้น")

    file_extension = os.path.splitext(file.filename)[1]
    new_file_name = f"{uuid.uuid4()}{file_extension}"
    contents = await file.read()

    try:
        image_url = await storage_service.upload_file(
            file_content=contents,
            file_name=new_file_name,
            content_type=file.content_type,
            folder="profile",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"เกิดข้อผิดพลาดในการอัปโหลดรูปภาพ: {str(e)}"
        )

    user_in = UserCreate(
        first_name=first_name,
        last_name=last_name,
        email=email,
        password=password,
        profile_image_url=image_url,
    )

    user = await user_crud.register(db, user=user_in)
    return user


@router.post("/refresh", response_model=Token)
@router.post("/refresh-token", response_model=Token)
async def refresh_token(
    refresh_data: Optional[RefreshTokenRequest] = None,
    refresh_token: Optional[str] = None,
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    """
    ตรวจสอบ Refresh Token และออก Access Token ใหม่
    """
    token_str = None
    if refresh_data:
        token_str = refresh_data.refresh_token or refresh_data.refreshToken
    if not token_str and refresh_token:
        token_str = refresh_token

    if not token_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="กรุณาระบุ refresh token",
        )

    try:
        payload = security.jwt.decode(
            token_str, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_data = payload.get("sub")
        if token_data is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="สิทธิ์การเข้าถึงไม่ถูกต้อง หรือโทเค็นหมดอายุ",
            )
        user_id = int(token_data)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="สิทธิ์การเข้าถึงไม่ถูกต้อง หรือโทเค็นหมดอายุ",
        )

    user = await user_crud.get_user_by_id(db, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ไม่พบข้อมูลผู้ใช้งานในระบบ",
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(
            subject=user.id,
            role=user.role,
            expires_delta=access_token_expires,
        ),
        "refresh_token": token_str,
        "token_type": "bearer",
        "user": user,
    }


@router.post("/logout")
async def logout():
    """
    ออกจากระบบ
    """
    return {"message": "ออกจากระบบสำเร็จ"}
