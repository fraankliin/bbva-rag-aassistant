# app/services/analytics_service.py

import logging
from typing import Dict, Any, List
from app.repositories.analytics_repository import AnalyticsRepository

logger = logging.getLogger("app.services.analytics_service")


class AnalyticsService:


    def __init__(self, repository: AnalyticsRepository):
        self.repository = repository

    def compile_user_dashboard(self, user_id: str) -> Dict[str, Any]:
        logger.info(f"Compilando dashboard analítico personalizado para el usuario: {user_id}")

        # 1. Obtener conteos filtrados
        counts = self.repository.get_user_specific_counts(user_id)
        user_convs = counts["user_conversations"]
        user_msgs = counts["user_messages"]

        # 2. Procesar mensajes del usuario (Frecuencias y latencias experimentadas)
        raw_messages = self.repository.get_user_messages_metadata(user_id)

        conv_lengths = {}  # Guardará el conteo: {conversation_id: cantidad_mensajes}
        conv_titles = {}  # Guardará el mapeo: {conversation_id: titulo_conversacion}
        query_counts = {}
        assistant_latencies = []
        slowest_responses = []

        for msg in raw_messages:
            c_id = msg["conversation_id"]
            role = msg["role"]

            # Extraemos el título desde la relación anidada de Supabase
            conv_info = msg.get("conversations") or {}
            c_title = conv_info.get("title", "Conversación sin título")
            conv_titles[c_id] = c_title

            # Contar mensajes por sesión
            conv_lengths[c_id] = conv_lengths.get(c_id, 0) + 1

            if role == "user":
                query_text = msg["content"].strip()
                query_counts[query_text] = query_counts.get(query_text, 0) + 1
            elif role == "assistant":
                latency = msg.get("latency_ms")
                if latency is not None:
                    assistant_latencies.append(latency)
                    slowest_responses.append({"message_id": msg["id"], "latency_ms": latency})

        # Ordenamos las conversaciones por volumen de mensajes
        sorted_conv_lengths = sorted(conv_lengths.items(), key=lambda x: x[1], reverse=True)

        # AQUÍ APLICAMOS TU CAMBIO: Mapeamos usando el diccionario de títulos
        longest_conversations = [
            {
                "conversation_id": c[0],
                "conversation_title": conv_titles.get(c[0], "Conversación Activa"),
                "total_messages": c[1]
            }
            for c in sorted_conv_lengths[:5]
        ]

        max_messages_single_conv = sorted_conv_lengths[0][1] if sorted_conv_lengths else 0
        avg_msgs_per_conv = round(user_msgs / user_convs, 2) if user_convs > 0 else 0

        # Rendimiento de la IA experimentada por este usuario
        total_replies = len(assistant_latencies)
        avg_latency_ms = round(sum(assistant_latencies) / total_replies, 2) if total_replies > 0 else 0

        top_frequent_queries = sorted(
            [{"query": k, "frequency": v} for k, v in query_counts.items()],
            key=lambda x: x["frequency"], reverse=True
        )[:5]

        # 3. Procesar Métricas RAG (Qué temas le interesan a este usuario específico)
        raw_retrievals = self.repository.get_user_retrievals_metadata(user_id)
        total_retrievals = len(raw_retrievals)

        chunk_usages = {}
        doc_usages = {}
        total_similarity_score = 0.0

        for r in raw_retrievals:
            total_similarity_score += r.get("similarity_score") or 0.0
            chunk_info = r.get("document_chunks") or {}

            chunk_text = chunk_info.get("chunk_text", "Fragmento sin texto")[:80] + "..."
            chunk_usages[chunk_text] = chunk_usages.get(chunk_text, 0) + 1

            doc_info = chunk_info.get("documents") or {}
            doc_title = doc_info.get("title", "Documento sin título")
            doc_usages[doc_title] = doc_usages.get(doc_title, 0) + 1

        avg_similarity = round(total_similarity_score / total_retrievals, 4) if total_retrievals > 0 else 0.0
        top_chunks = sorted([{"chunk_snippet": k, "usages": v} for k, v in chunk_usages.items()],
                            key=lambda x: x["usages"], reverse=True)[:5]
        top_documents = sorted([{"document_title": k, "usages": v} for k, v in doc_usages.items()],
                               key=lambda x: x["usages"], reverse=True)[:5]

        return {
            "status": "success",
            "user_context_id": user_id,
            "overview": {
                "your_total_conversations": user_convs,
                "your_total_messages_sent_and_received": user_msgs,
                "system_indexed_documents": counts["total_documents"],
                "system_indexed_chunks": counts["total_chunks"]
            },
            "your_conversation_behavior": {
                "your_average_messages_per_conversation": avg_msgs_per_conv,
                "your_longest_conversations": longest_conversations
            },
            "ai_performance_experienced": {
                "average_response_time_ms": avg_latency_ms,
                "average_response_time_seconds": round(avg_latency_ms / 1000, 2)
            },
            "your_rag_interest_metrics": {
                "average_context_similarity_score": avg_similarity,
                "your_most_consulted_banking_documents": top_documents,
                "your_most_retrieved_chunks": top_chunks
            },
            "your_top_queries": {
                "most_frequent_queries_top_5": top_frequent_queries
            }
        }