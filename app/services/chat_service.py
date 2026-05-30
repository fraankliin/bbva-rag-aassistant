
import logging
from typing import Dict, Any, List
from app.services.search_service import SearchService
from app.providers.llm.base_llm import BaseLLMProvider
from app.core.prompts import RAG_SYSTEM_PROMPT_V1

logger = logging.getLogger("app.services.chat_service")


class ChatService:
    """
    Servicio de orquestación RAG agnóstico al modelo de lenguaje.
    """

    def __init__(self, search_service: SearchService, llm_provider: BaseLLMProvider):
        self.search_service = search_service
        self.llm_provider = llm_provider  # Inyección de dependencias de cualquier proveedor

    def _build_context_text(self, chunks: List[Dict[str, Any]]) -> str:
        context_text = ""
        for i, chunk in enumerate(chunks, 1):
            source = chunk.get("metadata", {}).get("source_url", "Web BBVA")
            context_text += f"--- FRAGMENTO {i} (Fuente: {source}) ---\n"
            context_text += f"{chunk['chunk_text']}\n\n"
        return context_text

    async def answer_user_question(
            self,
            user_query: str,
            match_threshold: float = 0.40,
            top_k: int = 4
    ) -> Dict[str, Any]:
        try:
            # 1. Recuperación semántica desde Supabase
            relevant_chunks = self.search_service.search_relevant_chunks(
                query_text=user_query,
                match_threshold=match_threshold,
                match_count=top_k
            )



            context_text = self._build_context_text(relevant_chunks)




            # 2. Definición de instrucciones del sistema
            system_instruction = RAG_SYSTEM_PROMPT_V1.format(context_text=context_text)

            # 3. Consumo del LLM a través de la Interfaz Abstracta
            user_message = f"Pregunta del usuario: {user_query}"

            llm_answer = self.llm_provider.generate_response(
                system_instruction=system_instruction,
                user_message=user_message,
                temperature=0.2
            )

            sources = list(set([chunk.get("metadata", {}).get("source_url") for chunk in relevant_chunks]))

            return {
                "answer": llm_answer,
                "sources_used": sources,
                "debug": {"chunks_count": len(relevant_chunks)}
            }

        except Exception as e:
            logger.error(f"Error en el flujo del ChatService: {str(e)}")
            raise e