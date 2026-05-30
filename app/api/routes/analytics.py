# app/api/routes/analytics.py

import logging
from fastapi import APIRouter, status, HTTPException, Depends

from app.core.security import get_current_user
from app.services.analytics_service import AnalyticsService
from app.repositories.analytics_repository import AnalyticsRepository

logger = logging.getLogger("app.api.routes.analytics")

router = APIRouter(
    prefix="/analytics",
    tags=["Analítica e Impacto"]
)


# Proveedores de dependencias (Factory Pattern / Inyección de FastAPI)



def get_analytics_service():

    analytic_repository = AnalyticsRepository()

    analytics_service = AnalyticsService(analytic_repository)

    return analytics_service


@router.get(
    "/dashboard",
    status_code=status.HTTP_200_OK,
    summary="Dashboard analítico integrado del sistema RAG",
    description="Analiza de punta a punta las interacciones del chat, rendimiento de velocidad del LLM y la relevancia de pgvector."
)
async def get_comprehensive_analytics(
        analytics_service: AnalyticsService = Depends(get_analytics_service),
        current_user=Depends(get_current_user)
):
    try:
        user_id_str = str(current_user.id)

        logger.info("Endpoint /analytics/dashboard invocado.")
        report = analytics_service.compile_user_dashboard(user_id=user_id_str)
        return report

    except Exception as e:
        logger.error(f"Error en el endpoint de analítica: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en el subsistema analítico: {str(e)}"
        )