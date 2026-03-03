import uuid
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.schemas.user import UserResponse
from app.services.storage_service import storage_service

from app.crud import user as user_crud

router = APIRouter()


@router.patch("/me", response_model=UserResponse)
async def update_user_me(
    background_tasks: BackgroundTasks,
    first_name: Optional[str] = Form(None),
    last_name: Optional[str] = Form(None),
    avatar: Optional[UploadFile] = File(None),
    current_user=Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(deps.get_db),
):
    """
    อัปเดตข้อมูลโปรไฟล์ผู้ใช้งาน (ส่งเฉพาะข้อมูลที่ต้องการเปลี่ยนได้)
    """
    user_id = current_user["id"]

    if first_name is not None or last_name is not None:
        new_first = first_name if first_name is not None else current_user["first_name"]
        new_last = last_name if last_name is not None else current_user["last_name"]

        await user_crud.update_user_name(
            db, user_id=user_id, first_name=new_first, last_name=new_last
        )

    if avatar is not None:
        old_avatar_url = current_user["profile_image_url"]

        file_content = await avatar.read()

        unique_filename = f"{uuid.uuid4().hex}_{avatar.filename}"

        new_avatar_url = await storage_service.upload_file(
            file_content=file_content,
            file_name=unique_filename,
            content_type=avatar.content_type,
            folder="profiles",
        )

        await user_crud.update_user_profile_image(
            db, user_id=user_id, profile_image_url=new_avatar_url
        )

        if old_avatar_url:
            background_tasks.add_task(storage_service.delete_file, old_avatar_url)

    updated_user = await user_crud.get_user_by_id(db, user_id=user_id)
    return updated_user
