from pydantic import BaseModel, EmailStr
from datetime import datetime


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    name: str
    is_admin: bool


class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: str
    is_admin: bool = False


class UserOut(BaseModel):
    id: int
    email: str
    name: str
    is_active: bool
    is_admin: bool
    created_at: datetime

    model_config = {"from_attributes": True}
