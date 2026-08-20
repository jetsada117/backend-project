from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.schemas.user import UserCreate, UserResponse, UserRole
from app.core.security import get_password_hash, verify_password


async def get_user_by_id(db: AsyncSession, user_id: int) -> UserResponse:
    """
    ดึงข้อมูลผู้ใช้จากฐานข้อมูลโดยใช้ ID
    """
    sql = text(
        "SELECT id, email, first_name, last_name, hashed_password, role, profile_image_url "
        "FROM users WHERE id = :id"
    )
    param = {"id": user_id}
    result = await db.execute(sql, param)
    row = result.mappings().first()
    return row


async def get_user_by_email(db: AsyncSession, email: str) -> UserResponse:
    """
    ดึงข้อมูลผู้ใช้จากฐานข้อมูลโดยใช้ Email
    """
    sql = text(
        "SELECT id, email, first_name, last_name, hashed_password, role, profile_image_url "
        "FROM users WHERE email = :email"
    )
    param = {"email": email}
    result = await db.execute(sql, param)
    row = result.mappings().first()
    return row


async def register(db: AsyncSession, user: UserCreate) -> UserResponse:
    """
    ลงทะเบียนผู้ใช้ใหม่พร้อม Hash Password และบันทึกลงฐานข้อมูล
    """
    hashed_password = get_password_hash(user.password)
    default_role = UserRole.USER.value

    sql = text(
        "INSERT INTO users (email, hashed_password, first_name, last_name, role, profile_image_url) "
        "VALUES (:email, :hashed_password, :first_name, :last_name, :role, :profile_image_url)"
    )

    param = {
        "email": user.email,
        "hashed_password": hashed_password,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": default_role,
        "profile_image_url": user.profile_image_url,
    }

    result = await db.execute(sql, param)
    new_id = result.lastrowid
    await db.commit()

    return {"message": "ลงทะเบียนสำเร็จ"}


async def authenticate_user(db: AsyncSession, email: str, password: str):
    """
    ตรวจสอบ Email และ Password แล้ว Return ข้อมูลผู้ใช้ถ้าถูกต้อง
    """
    user = await get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def update_user_profile_image(
    db: AsyncSession, user_id: int, profile_image_url: str
):
    """
    อัปเดต URL รูปโปรไฟล์ของผู้ใช้
    """
    sql = text("UPDATE users SET profile_image_url = :profile_image_url WHERE id = :id")
    param = {"profile_image_url": profile_image_url, "id": user_id}

    await db.execute(sql, param)
    await db.commit()

    return {"message": "อัปเดตรูปโปรไฟล์สำเร็จ"}


async def update_user_name(
    db: AsyncSession, user_id: int, first_name: str, last_name: str
):
    """
    อัปเดตชื่อและนามสกุลของผู้ใช้
    """
    sql = text(
        "UPDATE users SET first_name = :first_name, last_name = :last_name WHERE id = :id"
    )
    param = {"first_name": first_name, "last_name": last_name, "id": user_id}

    await db.execute(sql, param)
    await db.commit()

    return {"message": "อัปเดตชื่อผู้ใช้งานสำเร็จ"}
