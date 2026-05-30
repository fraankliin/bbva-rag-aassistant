import logging
from typing import List, Dict, Any
from app.db.database import supabase
logger = logging.getLogger("app.repositories.history_repository")


class HistoryRepository:


    def create_conversation(self, conversation_id: str, user_id: str, title: str) -> Dict[str, Any]:
        """Inserta una nueva sesión de conversación."""
        data = {
            "id": conversation_id,
            "user_id": user_id,
            "title": title
        }
        response = supabase.table("conversations").insert(data).execute()
        return response.data[0] if response.data else {}

    def get_messages_by_conversation(self, conversation_id: str, limit: int = 6) -> List[Dict[str, Any]]:

        response = supabase.table("messages") \
            .select("role, content, created_at") \
            .eq("conversation_id", conversation_id) \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()

        messages = response.data if response.data else []
        messages.reverse()
        return messages

    def save_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        response = supabase.table("messages").insert(message_data).execute()
        return response.data[0] if response.data else {}

    def save_bulk_retrievals(self, retrievals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not retrievals:
            return []
        response = supabase.table("message_retrievals").insert(retrievals).execute()
        return response.data if response.data else []

    def get_user_conversations_with_counts(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Trae todas las conversaciones de un usuario específico, ordenadas por 
        la última modificación, e incluye la relación de mensajes para contar el volumen.
        """
        response = supabase.table("conversations") \
            .select("id, title, created_at, updated_at, messages(id)") \
            .eq("user_id", user_id) \
            .order("updated_at", desc=True) \
            .execute()
        return response.data or []

    def get_conversation_details(self, conversation_id: str) -> Dict[str, Any] | None:
        """
        Recupera una conversación específica por su ID.
        """
        response = supabase.table("conversations") \
            .select("id, title, created_at, updated_at, user_id") \
            .eq("id", conversation_id) \
            .maybe_single() \
            .execute()
        return response.data

    def get_conversation_messages_with_sources(self, conversation_id: str) -> List[Dict[str, Any]]:
        """
        Recupera cronológicamente todos los mensajes de un hilo conversacional,
        incluyendo los fragmentos RAG recuperados del Scraper para el rol assistant.
        """
        response = supabase.table("messages") \
            .select("""
                id, role, content, latency_ms, created_at,
                message_retrievals(similarity_score, document_chunks(documents(title, url)))
            """) \
            .eq("conversation_id", conversation_id) \
            .order("created_at", desc=False) \
            .execute()
        return response.data or []