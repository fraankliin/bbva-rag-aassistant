import logging
from typing import List, Dict, Any
from app.providers.embeddings_provider import EmbeddingProvider
from app.db.database import supabase

logger = logging.getLogger("app.services.search_service")


class SearchService:

    def __init__(self, embedding_provider: EmbeddingProvider):
        self.embedding_provider = embedding_provider

    def search_relevant_chunks(
            self,
            query_text: str,
            match_threshold: float = 0.40,
            match_count: int = 4

    ) -> List[Dict[str, Any]]:

        """
        Toma una pregunta del usuario, la vectoriza de forma directa y consulta la RPC 'match_chunks'.
        """
        if not query_text or not query_text.strip():
            logger.warning("Se recibió una consulta vacía para búsqueda semántica.")
            return []

        try:
            logger.info(f"Procesando búsqueda semántica para: '{query_text}'")

            # 1. VECTORIZACIÓN DIRECTA DE LA PREGUNTA
            query_embedding = self.embedding_provider.model.encode(query_text).tolist()

            # 2. Invocamos la RPC en Supabase pasándole los parámetros exactos
            logger.info(
                f"Llamando a la RPC 'match_chunks' en Supabase (Top-K: {match_count}, Threshold: {match_threshold})")
            response = supabase.rpc(
                "match_chunks",
                {
                    "query_embedding": query_embedding,
                    "match_threshold": match_threshold,
                    "match_count": match_count
                }
            ).execute()

            results = response.data
            logger.info(f"Búsqueda finalizada. Se encontraron {len(results)} fragmentos relevantes.")
            return results

        except Exception as e:
            logger.error(f"Error crítico durante la recuperación semántica: {str(e)}")
            raise e
