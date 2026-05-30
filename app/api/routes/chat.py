import logging
from typing import Any

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



        # 3.orquestador del chat
        return ChatService(search_service=search_service, llm_provider=llm_provider, history_service=get_history_service())

    except Exception as e:
        logger.error(f"Error al inicializar las dependencias de ChatService: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al configurar el motor de inteligencia artificial."
        )

def get_history_service() :
    # repositorio historial
    history_repository = HistoryRepository()

    # servicio historial
    history_service = HistoryService(history_repository)

    return history_service


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


@router.get(
    "/conversations",
    status_code=status.HTTP_200_OK,
    summary="Listar conversaciones del usuario para el sidebar"
)
async def list_conversations(
        history_service: HistoryService = Depends(get_history_service),
        current_user: Any = Depends(get_current_user)
):
    try:
        user_id_str = str(current_user.id)
        return history_service.list_conversations_for_sidebar(user_id=user_id_str)
    except Exception as e:
        logger.error(f"Error al listar conversaciones: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error en el historial: {str(e)}")


@router.get(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_200_OK,
    summary="Obtener el detalle de una conversación específica"
)
async def get_conversation(
        conversation_id: str,
        history_service: HistoryService = Depends(get_history_service),
        current_user: Any = Depends(get_current_user)
):
    try:
        user_id_str = str(current_user.id)
        result = history_service.get_full_conversation_history(
            conversation_id=conversation_id,
            user_id=user_id_str
        )

        # Manejo de respuestas condicionales del servicio
        if "error" in result:
            if result["error"] == "not_found":
                raise HTTPException(status_code=404, detail=result["message"])
            elif result["error"] == "unauthorized":
                raise HTTPException(status_code=403, detail=result["message"])

        return result
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error al recuperar la conversación {conversation_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al procesar el hilo: {str(e)}")