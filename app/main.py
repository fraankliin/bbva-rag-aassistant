import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes.health import router as health_router
from app.api.routes.internal_users import router as internal_users_router
from app.api.routes.scraper import router as scraper_router
from app.api.routes.search import router as search_router
from app.api.routes.chat import router as chat_router
from app.api.routes.analytics import router as analytics_router
from app.providers.embeddings_provider import EmbeddingProvider
from app.providers.scraper.bbva_scraper import BBVAScraper
from app.repositories.document_repository import DocumentRepository
from app.services.indexer_service import IndexerService
from app.utils.text_splitter import DocumentTextSplitter
from app.core.logger import get_logger

logger = get_logger(__name__)


async def run_initial_scraper():
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


    logger.info("[STARTUP] Detectado inicio del sistema. Preparando Warm-up del Scraper...")

    try:
        await asyncio.sleep(4)

        scraper = BBVAScraper()
        splitter = DocumentTextSplitter(chunk_size=1000, chunk_overlap=200)
        embedding_provider = EmbeddingProvider(model_name="all-MiniLM-L6-v2")
        repository = DocumentRepository()

        indexer_service = IndexerService(
            scraper=scraper,
            splitter=splitter,
            embedding_provider=embedding_provider,
            document_repository=repository
        )


        logger.info("[STARTUP] Iniciando Web Scraping automático e indexación vectorial en Supabase...")

        resultados = await asyncio.to_thread(indexer_service.scrape_and_save_documents, SEED_URLS)
        logger.info("[STARTUP] Web Scraping inicial completado con éxito. Base de conocimientos actualizada.")

    except Exception as e:
        logger.error(f"[STARTUP] Error crítico durante el scraping automatizado de inicio: {str(e)}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(run_initial_scraper())
    logger.info("[FASTAPI] Tarea en segundo plano registrada. Servidor listo para recibir peticiones HTTP.")

    yield

    # Lógica opcional que se ejecutaría al apagar la aplicación (Shutdown)
    logger.info("[FASTAPI] Apagando el servidor...")



app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan
)


# CORS
origins = [
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health_router)
app.include_router(internal_users_router)
app.include_router(scraper_router)
app.include_router(search_router)
app.include_router(chat_router)
app.include_router(analytics_router)

