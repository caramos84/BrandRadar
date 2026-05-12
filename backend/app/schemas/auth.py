from pydantic import BaseModel, EmailStr

from app.schemas.user import UserResponse


class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    work_role: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class MessageResponse(BaseModel):
    message: str
