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

    def get_formatted_chat_history(self, conversation_id: str, limit: int = 6) -> str:

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