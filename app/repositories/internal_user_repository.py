from app.db.database import supabase

class InternalUserRepository:

    @staticmethod
    async def create_internal_user(user_data: dict):

        response = (
            supabase
            .table('internal_users')
            .insert(user_data)
            .execute()
        )

        return response.data[0]