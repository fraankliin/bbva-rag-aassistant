from app.db.database import supabase
from app.core.logger import get_logger
logger = get_logger(__name__)

class AuthRepository:

    @staticmethod
    async def register_user(
        email: str,
        password: str
    ):

        response = supabase.auth.sign_up(
            {
                "email": email,
                "password": password
            }
        )

        return response

    @staticmethod
    async def login_user(
        email: str,
        password: str
    ):

        response = supabase.auth.sign_in_with_password(
            {
                "email": email,
                "password": password
            }
        )

        return response