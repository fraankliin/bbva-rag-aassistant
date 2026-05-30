from fastapi import APIRouter, Depends, BackgroundTasks, status
from langchain_text_splitters import TextSplitter
from torch.nn.functional import embedding
from app.core.security import get_current_user
from app.providers.embeddings_provider import EmbeddingProvider
from app.services.indexer_service import IndexerService
from app.providers.scraper.bbva_scraper import BBVAScraper
from app.core.config import settings
from app.repositories.document_repository import DocumentRepository
from app.utils.text_splitter import DocumentTextSplitter

SEED_URLS = [
    'https://www.bbva.com.co/personas/productos/cuentas/ahorro/nomina.html',
    'https://www.bbva.com.co/personas/productos/cuentas/ahorro/pensionados.html',
    'https://www.bbva.com.co/personas/productos/cuentas.html',
    'https://www.bbva.com.co/personas/productos/tarjetas/debito.html',
    'https://www.bbva.com.co/personas/productos/tarjetas/credito/mastercard/black.html',
    'https://www.bbva.com.co/personas/productos/prestamos/consumo/libre-inversion.html',
    'https://www.bbva.com.co/personas/productos/prestamos/consumo/libranza.html',
    'https://www.bbva.com.co/personas/servicios-digitales/app-bbva.html',
    'https://www.bbva.com.co/personas/servicios-digitales/net.html'
]

router = APIRouter(prefix="/scraper", tags=["Scraper"])


def get_indexer_service() -> IndexerService:
    """
    Dependency Injection Factory para construir el IndexerService
    con todas sus piezas e infraestructura local resueltas.
    """
    # Instanciamos los componentes que desarrollamos
    scraper = BBVAScraper()
    splitter = DocumentTextSplitter(chunk_size=1000, chunk_overlap=200)
    embedding_provider = EmbeddingProvider(model_name="all-MiniLM-L6-v2")
    repository = DocumentRepository()

    # Construimos y retornamos el orquestador con sus 4 motores listos
    return IndexerService(
        scraper=scraper,
        splitter=splitter,
        embedding_provider=embedding_provider,
        document_repository=repository
    )


@router.post("/trigger", status_code=status.HTTP_202_ACCEPTED)
async def trigger_scraping(
        background_tasks: BackgroundTasks,
        current_user=Depends(get_current_user),
        indexer_service: IndexerService = Depends(get_indexer_service)

):
    """
    Endpoint administrativo para disparar la indexación y vectorización
    de las URLs semilla en segundo plano (Background Tasks).
    """
    background_tasks.add_task(indexer_service.scrape_and_save_documents, SEED_URLS)
    return {
        "status": "processing",
        "message": f"Se ha iniciado el pipeline de indexación para {len(SEED_URLS)} URLs en segundo plano.",
        "seed_urls": SEED_URLS
    }
