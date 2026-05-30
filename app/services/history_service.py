# app/services/history_service.py

import logging
import uuid
from typing import List, Dict, Any
from app.repositories.history_repository import HistoryRepository

logger = logging.getLogger("app.services.history_service")


class HistoryService:


    def __init__(self, repository: HistoryRepository):
        self.repository = repository

    def initialize_conversation_if_needed(self, conversation_id: str | None, user_query: str, user_id: str) -> str:

        if conversation_id:
            return conversation_id

        new_conv_id = str(uuid.uuid4())
        title = " ".join(user_query.split()[:5]) + "..."


        logger.info(f"Creando nueva conversación en base de datos con ID: {new_conv_id}")
        self.repository.create_conversation(new_conv_id, user_id, title)
        return new_conv_id

    def get_formatted_chat_history(self, conversation_id: str, limit: int = 5) -> str:

        raw_messages = self.repository.get_messages_by_conversation(conversation_id, limit)
        if not raw_messages:
            return "No hay mensajes previos en esta sesión.\n"

        formatted_history = ""
        for msg in raw_messages:
            role_label = "Usuario" if msg["role"] == "user" else "Asesor (Tú)"
            formatted_history += f"{role_label}: {msg['content']}\n"

        return formatted_history

    def register_user_message(self, conversation_id: str, message_id: str, content: str):
        data = {
            "id": message_id,
            "conversation_id": conversation_id,
            "role": "user",
            "content": content,
            "prompt_tokens": None,  # Se pueden calcular o dejar null en el request inicial
            "completion_tokens": None,
            "latency_ms": None
        }
        self.repository.save_message(data)

    def register_assistant_response(
            self,
            conversation_id: str,
            content: str,
            latency_ms: int,
            prompt_tokens: int = 0,
            completion_tokens: int = 0
    ):
        data = {
            "id": str(uuid.uuid4()),
            "conversation_id": conversation_id,
            "role": "assistant",
            "content": content,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "latency_ms": latency_ms
        }
        self.repository.save_message(data)

    def register_rag_auditory(self, message_id: str, relevant_chunks: List[Dict[str, Any]]):

        retrieval_records = []
        for chunk in relevant_chunks:
            retrieval_records.append({
                "id": str(uuid.uuid4()),
                "message_id": message_id,
                "chunk_id": chunk.get("id"),  # El ID del chunk que viene de document_chunks
                "similarity_score": chunk.get("similarity")  # El score float8 de pgvector
            })

        if retrieval_records:
            self.repository.save_bulk_retrievals(retrieval_records)

    def list_conversations_for_sidebar(self, user_id: str) -> List[Dict[str, Any]]:
        """Procesa la lista de conversaciones e inyecta el conteo dinámico de mensajes."""
        raw_conversations = self.repository.get_user_conversations_with_counts(user_id)
        formatted_list = []

        for conv in raw_conversations:
            # messages(id) nos devuelve una lista de diccionarios, calculamos su longitud
            msg_list = conv.get("messages", [])
            messages_count = len(msg_list) if isinstance(msg_list, list) else 0

            formatted_list.append({
                "id": conv["id"],
                "title": conv["title"],
                "created_at": conv["created_at"],
                "updated_at": conv["updated_at"],
                "messages_count": messages_count
            })

        return formatted_list

    def get_full_conversation_history(self, conversation_id: str, user_id: str) -> Dict[str, Any]:
        """Construye el árbol completo de la conversación validando pertenencia."""
        # 1. Validar existencia y propiedad de la conversación
        conversation = self.repository.get_conversation_details(conversation_id)
        if not conversation:
            return {"error": "not_found", "message": "La conversación solicitada no existe."}

        if str(conversation["user_id"]) != user_id:
            return {"error": "unauthorized", "message": "No tienes permisos para acceder a este historial."}

        # 2. Traer mensajes y mapear fuentes
        raw_messages = self.repository.get_conversation_messages_with_sources(conversation_id)
        formatted_messages = []

        for msg in raw_messages:
            msg_data = {
                "id": msg["id"],
                "role": msg["role"],
                "content": msg["content"],
                "created_at": msg["created_at"]
            }

            # Si es el asistente, estructuramos las telemetrías y las fuentes del RAG
            if msg["role"] == "assistant":
                msg_data["latency_ms"] = msg.get("latency_ms")

                # Extraer y remover duplicados de las fuentes utilizadas en pgvector
                sources = []
                seen_urls = set()

                retrievals = msg.get("message_retrievals") or []
                for ret in retrievals:
                    chunk = ret.get("document_chunks") or {}
                    doc = chunk.get("documents") or {}
                    url = doc.get("url")

                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        sources.append({
                            "document_title": doc.get("title", "Documento Institucional"),
                            "url": url,
                            "similarity_score": ret.get("similarity_score")
                        })

                msg_data["sources_used"] = sources

            formatted_messages.append(msg_data)

        return {
            "id": conversation["id"],
            "title": conversation["title"],
            "created_at": conversation["created_at"],
            "updated_at": conversation["updated_at"],
            "messages": formatted_messages
        }