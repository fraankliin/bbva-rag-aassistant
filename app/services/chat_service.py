
import logging
import time
import uuid
from typing import Dict, Any, List

from app.services.history_service import HistoryService
from app.services.search_service import SearchService
from app.providers.llm.base_llm import BaseLLMProvider
from app.core.prompts import RAG_SYSTEM_PROMPT_V1

logger = logging.getLogger("app.services.chat_service")


class ChatService:


    def __init__(self, search_service: SearchService, llm_provider: BaseLLMProvider, history_service: HistoryService):
        self.search_service = search_service
        self.llm_provider = llm_provider
        self.history_service = history_service

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
            user_id: str,
            match_threshold: float = 0.40,
            conversation_id: str | None = None,
            top_k: int = 4
    ) -> Dict[str, Any]:
        try:
            #Inicializar o verificar la conversación (Tabla 'conversations')
            active_conv_id = self.history_service.initialize_conversation_if_needed(
                conversation_id=conversation_id,
                user_query=user_query,
                user_id = user_id
            )

            #Generar ID único para este mensaje de usuario y registrarlo
            user_message_id = str(uuid.uuid4())
            self.history_service.register_user_message(
                conversation_id=active_conv_id,
                message_id=user_message_id,
                content=user_query
            )

            # 1. Recuperación semántica desde Supabase
            relevant_chunks = self.search_service.search_relevant_chunks(
                query_text=user_query,
                match_threshold=match_threshold,
                match_count=top_k
            )



            context_text = self._build_context_text(relevant_chunks)

            #Dejamos guardado qué chunks causaron la respuesta a este 'user_message_id'
            self.history_service.register_rag_auditory(
                message_id=user_message_id,
                relevant_chunks=relevant_chunks
            )

            #Extraer memoria histórica formateada (Tabla 'messages')
            chat_history_text = self.history_service.get_formatted_chat_history(
                conversation_id=active_conv_id,
                limit=5)


            # 2. Definición de instrucciones del sistema
            system_instruction = RAG_SYSTEM_PROMPT_V1.format(chat_history=chat_history_text,context_text=context_text)

            # 3. Consumo del LLM a través de la Interfaz Abstracta
            user_message = f"Pregunta del usuario: {user_query}"

            logger.info(f"Llamando al LLM para la conversación {active_conv_id}...")
            start_time = time.perf_counter()
            llm_answer = self.llm_provider.generate_response(
                system_instruction=system_instruction,
                user_message=user_message,
                temperature=0.2
            )

            end_time = time.perf_counter()

            latency_ms = int((end_time - start_time) * 1000)
            logger.info(f"LLM respondió en {latency_ms} ms.")

            #Registrar la respuesta del bot con métricas (Tabla 'messages')
            self.history_service.register_assistant_response(
                conversation_id=active_conv_id,
                content=llm_answer,
                latency_ms=latency_ms,
                prompt_tokens=0,
                completion_tokens=0
            )

            sources = list(set([chunk.get("metadata", {}).get("source_url") for chunk in relevant_chunks]))

            return {
                "conversation_id": active_conv_id,
                "answer": llm_answer,
                "sources_used": sources,
                "debug": {
                    "chunks_count": len(relevant_chunks),
                    "latency_ms": latency_ms
                }
            }

        except Exception as e:
            logger.error(f"Error en el flujo del ChatService: {str(e)}")
            raise e