from fastapi import APIRouter, Depends, Query, status
from app.services.search_service import SearchService
from app.providers.embeddings_provider import EmbeddingProvider
from app.core.security import get_current_user

router = APIRouter(prefix="/search", tags=["Buscador Semántico (RAG - Retrieval)"])


def get_search_service() -> SearchService:
    embedding_provider = EmbeddingProvider()
    return SearchService(embedding_provider=embedding_provider)


@router.get("/test", status_code=status.HTTP_200_OK)
async def test_retrieval(
        query: str = Query(..., description="Escribe la pregunta o frase que deseas buscar semánticamente"),
        limit: int = Query(4, description="Número de fragmentos a recuperar (Top-K)"),
        threshold: float = Query(0.60, description="Umbral de similitud mínimo (0.0 - 1.0)"),
        search_service: SearchService = Depends(get_search_service),
        current_user=Depends(get_current_user),

):

    results = search_service.search_relevant_chunks(
        query_text=query,
        match_threshold=threshold,
        match_count=limit
    )

    return {
        "query": query,
        "total_recovered": len(results),
        "params": {
            "top_k": limit,
            "threshold": threshold
        },
        "chunks_recovered": results
    }