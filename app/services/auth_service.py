from fastapi import HTTPException
from markdown_it.parser_block import LOGGER
from supabase_auth.errors import AuthApiError
from werkzeug.security import generate_password_hash

from app.repositories.auth_repository import AuthRepository
from app.repositories.internal_user_repository import InternalUserRepository

from app.schemas.auth_schema import RegisterRequest, LoginRequest
from app.core.logger import get_logger

logger = get_logger(__name__)

class InternalUserService:

    @staticmethod
    async def create_internal_user(user_data: RegisterRequest):
        try:
            auth_response = await AuthRepository.register_user(
                user_data["email"],
                user_data["password"]
            )

        except AuthApiError as e:
            logger.error(f"Supabase Auth error: {str(e)}")

            # aquí controlas el error
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Error creando usuario en Supabase",
                    "reason": str(e)
                }
            )

        auth_user = auth_response.user

        if not auth_user:
            raise HTTPException(
                status_code=500,
                detail="No se pudo crear el usuario"
            )

        logger.info(f"Creando usuario: {auth_user}")

        internal_user = await InternalUserRepository.create_internal_user({
            "auth_user_id": auth_user.id,
            "name": user_data["name"],
            "last_name": user_data["last_name"]
        })

        return internal_user

    @staticmethod
    async def login(user):

        try:
            auth_response = await AuthRepository.login_user(
                user.email,
                user.password
            )

        except AuthApiError:
            raise HTTPException(
                status_code=401,
                detail="Credenciales inválidas"
            )

        session = auth_response.session
        user_data = auth_response.user

        if not session or not user_data:
            raise HTTPException(
                status_code=401,
                detail="Credenciales inválidas"
            )

        return {
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
            "token_type": "bearer",
            "user": {
                "id": user_data.id,
                "email": user_data.email
            }
        }