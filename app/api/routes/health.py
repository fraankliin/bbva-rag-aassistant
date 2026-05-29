from fastapi import APIRouter
from app.core.logger import get_logger
logger = get_logger(__name__)

router = APIRouter()



@router.get("/health", tags=["health"])
async def health_check():
    logger.info(f"Health called")
    return {"status": "ok"}