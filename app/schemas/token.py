from typing import Optional
from pydantic import BaseModel

from app.schemas.user import UserResponse


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user: UserResponse


class TokenPayload(BaseModel):
    sub: Optional[str] = None
    type: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: Optional[str] = None
    refreshToken: Optional[str] = None
