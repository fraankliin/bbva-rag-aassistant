from typing import Optional, Any, Dict

from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    name: str
    last_name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class UserLoginResponse(BaseModel):
    access_token: str
    token_type: str
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None
    user: Dict[str, Any]