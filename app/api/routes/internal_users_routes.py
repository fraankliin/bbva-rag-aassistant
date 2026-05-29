from fastapi import APIRouter

from app.schemas.auth_schema import RegisterRequest
from app.schemas.internal_user import InternalUserCreate, InternalUserResponse
from app.schemas.auth_schema import LoginRequest, UserLoginResponse
from app.services.auth_service import InternalUserService


router = APIRouter(prefix="/internal-users", tags=["Internal Users"])

@router.post("/register",response_model=InternalUserResponse)
async def create_internal_user(user: InternalUserCreate):

    return await InternalUserService.create_internal_user(user.model_dump())


@router.post("/login",response_model=UserLoginResponse)
async def login_internal_user(user: LoginRequest):


    return await InternalUserService.login(user)
