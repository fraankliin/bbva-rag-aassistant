from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from app.db.database import supabase

security = HTTPBearer()

async def get_current_user(credentials=Depends(security)):
    token = credentials.credentials

    user_response = supabase.auth.get_user(token)

    if not user_response.user:
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )

    return user_response.user