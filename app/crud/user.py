from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.schemas.user import UserBase, UserCreate, UserResponse

from app.core.security import get_password_hash, verify_password


async def get_user_by_id(db: AsyncSession, user_id: int) -> UserResponse:
    sql = text(
        "SELECT id, email, first_name, last_name, hashed_password, role FROM users WHERE id = :id"
    )
    param = {"id": user_id}
    result = await db.execute(sql, param)
    row = result.mappings().first()
    return row


async def get_user_by_email(db: AsyncSession, email: str) -> UserResponse:
    sql = text(
        "SELECT id, email, first_name, last_name, hashed_password, role FROM users WHERE email = :email"
    )
    param = {"email": email}
    result = await db.execute(sql, param)
    row = result.mappings().first()
    return row


# ฟังก์ชันสร้างผู้ใช้ใหม่
async def register(db: AsyncSession, user: UserCreate) -> UserResponse:
    hashed_password = get_password_hash(user.password)

    sql = text(
        "INSERT INTO users (email, hashed_password, first_name, last_name, role) "
        "VALUES (:email, :hashed_password, :first_name, :last_name, :role)"
    )

    param = {
        "email": user.email,
        "hashed_password": hashed_password,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": user.role,
    }

    result = await db.execute(sql, param)
    new_id = result.lastrowid
    await db.commit()

    return UserResponse(
        id=new_id,
        email=user.email,
        hashed_password=hashed_password,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role,
    )


async def authenticate_user(db: AsyncSession, email: str, password: str):
    user = await get_user_by_email(db, email)

    if not user:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user
