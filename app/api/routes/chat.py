import logging
from fastapi import APIRouter, Depends, HTTPException, status

from app.providers.embeddings_provider import EmbeddingProvider
from app.repositories.history_repository import HistoryRepository
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.history_service import HistoryService
from app.services.search_service import SearchService
from app.services.chat_service import ChatService
from app.providers.llm.gemini_provider import GeminiLLMProvider
from app.core.security import get_current_user

logger = logging.getLogger("app.api.routes.chat")

router = APIRouter(
    prefix="/chat",
    tags=["Chat RAG (Generación)"]
)


# Factoría para inicializar los servicios y el LLM con Inversión de Dependencias
def get_chat_service() -> ChatService:
    try:
        #  buscador semántico
        embedding_provider = EmbeddingProvider()
        search_service = SearchService(embedding_provider)

        # proveedor de IA.
        llm_provider = GeminiLLMProvider()

        # repositorio historial
        history_repository = HistoryRepository()

        # servicio historial
        history_service = HistoryService(history_repository)

        # 3.orquestador del chat
        return ChatService(search_service=search_service, llm_provider=llm_provider, history_service=history_service)

    except Exception as e:
        logger.error(f"Error al inicializar las dependencias de ChatService: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al configurar el motor de inteligencia artificial."
        )


@router.post(
    "/ask",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Consultar al asesor virtual (Pipeline RAG completo)",
    description="Recibe una pregunta, extrae contexto relevante de Supabase mediante pgvector y genera una respuesta con Gemini."
)
async def ask_assistant(
        payload: ChatRequest,
        current_user=Depends(get_current_user),
        chat_service: ChatService = Depends(get_chat_service)

):
    try:
        logger.info(f"Endpoint /chat/ask invocado con la query: '{payload.query}'")

        result = await chat_service.answer_user_question(
            user_query=payload.query,
            conversation_id=payload.conversation_id,
            user_id=str(current_user.id),
            match_threshold=payload.threshold,
            top_k=payload.top_k
        )
        return result

    except Exception as e:
        logger.error(f"Error en el endpoint de chat al procesar la solicitud: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en el procesamiento de la respuesta: {str(e)}"
        )
