from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class ChatRequest(BaseModel):
    query: str = Field(
        ...,
        description="La pregunta o consulta semántica del usuario sobre el banco.",
        example="¿Cuáles son los requisitos para abrir una cuenta de nómina?"
    )
    threshold: Optional[float] = Field(
        0.40,
        description="Umbral mínimo de similitud de coseno para los vectores.",
        ge=0.0, le=1.0
    )
    top_k: Optional[int] = Field(
        4,
        description="Cantidad máxima de fragmentos de contexto a recuperar.",
        ge=1, le=10
    )

class ChatResponse(BaseModel):
    answer: str = Field(..., description="Respuesta conversacional final generada por el LLM.")
    sources_used: List[str] = Field(..., description="Lista de URLs únicas de donde se extrajo la información.")
    debug: Dict[str, Any] = Field(..., description="Metadatos técnicos para auditoría del RAG.")