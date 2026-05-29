from pydantic import BaseModel, EmailStr


class InternalUserCreate(BaseModel):
    name: str
    last_name: str
    email: EmailStr
    password: str

class InternalUserResponse(BaseModel):
    name: str
    last_name: str
    auth_user_id: str