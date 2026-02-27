from datetime import timedelta
import os
from typing import Any
import uuid
from fastapi import (
    APIRouter,
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
from app.schemas.token import Token
from app.schemas.user import UserResponse, UserCreate
from app.crud import user as user_crud
from app.services.storage_service import storage_service

router = APIRouter()


@router.post("/login", response_model=Token)
async def login_access_token(
    request: Request,
    db: AsyncSession = Depends(deps.get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Any:
    user = await user_crud.authenticate_user(
        db, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    return {
        "access_token": security.create_access_token(
            subject=user.id,
            role=user.role,
            expires_delta=access_token_expires,
        ),
        "refresh_token": security.create_refresh_token(user.id),
        "token_type": "bearer",
    }


@router.post("/register", response_model=UserResponse)
async def register_user(
    *,
    db: AsyncSession = Depends(deps.get_db),
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    file: UploadFile = File(...),
) -> Any:
    user_exists = await user_crud.get_user_by_email(db, email=email)

    if user_exists:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
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


@router.post("/refresh-token", response_model=Token)
async def refresh_token(
    refresh_token: str,
) -> Any:
    try:
        payload = security.jwt.decode(
            refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_data = payload.get("sub")
        if token_data is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(
            token_data, expires_delta=access_token_expires
        ),
        "refresh_token": refresh_token,  # Return the same refresh token or rotate it
        "token_type": "bearer",
    }


@router.post("/logout")
async def logout():
    return {"message": "Successfully logged out"}
