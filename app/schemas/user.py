from typing import Optional
from pydantic import BaseModel, EmailStr
from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"


class UserBase(BaseModel):
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class UserCreate(UserBase):
    email: EmailStr
    password: str
    first_name: str
    last_name: str


class UserUpdate(UserBase):
    password: Optional[str] = None
    role: Optional[UserRole] = None


class UserResponse(UserBase):
    id: int
    email: EmailStr
    first_name: str
    last_name: str
    role: UserRole
