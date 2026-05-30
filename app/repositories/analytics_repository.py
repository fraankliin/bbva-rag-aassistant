# app/repositories/analytics_repository.py

import logging
from typing import List, Dict, Any
from app.db.database import supabase

logger = logging.getLogger("app.repositories.analytics_repository")

class AnalyticsRepository:
    """
    Repositorio especializado en la extracción de datos históricos
    y agregaciones transaccionales para auditoría y analítica en Supabase.
    """

    def get_user_specific_counts(self, user_id: str) -> Dict[str, int]:
        """Obtiene conteos globales de documentos y los específicos del usuario logueado."""
        # Filtramos conversaciones que pertenecen al usuario
        convs_count = supabase.table("conversations").select("id", count="exact").eq("user_id",
                                                                                          user_id).execute().count or 0

        # Filtramos mensajes cruzando con sus conversaciones
        msgs_resp = supabase.table("messages").select("id, conversations!inner(user_id)").eq(
            "conversations.user_id", user_id).execute()
        msgs_count = len(msgs_resp.data) if msgs_resp.data else 0

        # Datos globales de la base de conocimiento (Scraper)
        docs_count = supabase.table("documents").select("id", count="exact").execute().count or 0
        chunks_count = supabase.table("document_chunks").select("id", count="exact").execute().count or 0

        return {
            "user_conversations": convs_count,
            "user_messages": msgs_count,
            "total_documents": docs_count,
            "total_chunks": chunks_count
        }

    def get_user_messages_metadata(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Recupera la metadata de los mensajes pertenecientes al usuario del JWT,
        incluyendo el título de la conversación para el cálculo de rankings.
        """
        response = supabase.table("messages") \
            .select("id, conversation_id, role, content, latency_ms, created_at, conversations!inner(user_id, title)") \
            .eq("conversations.user_id", user_id) \
            .execute()
        return response.data or []

    def get_user_retrievals_metadata(self, user_id: str) -> List[Dict[str, Any]]:
        """Trae los registros de auditoría RAG causados por las consultas de este usuario específico."""
        response = supabase.table("message_retrievals") \
            .select(
            "chunk_id, similarity_score, messages!inner(id, conversations!inner(user_id)), document_chunks(chunk_text, documents(title))") \
            .eq("messages.conversations.user_id", user_id) \
            .execute()
        return response.data or []