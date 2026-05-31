from typing import Any, List, Dict
from app.core.logger import get_logger
from app.providers.embeddings_provider import EmbeddingProvider
from app.providers.scraper.base import BaseScraper
from app.repositories.document_repository import DocumentRepository
from app.utils.text_splitter import DocumentTextSplitter

logger = get_logger(__name__)


class IndexerService:
    """
    Servicio Orquestador principal de la fase de datos.
    Coordina secuencialmente el scraping, la fragmentación, la vectorización local
    y la persistencia relacional/vectorial en Supabase.
    """

    def __init__(
            self,
            scraper: BaseScraper,
            splitter: DocumentTextSplitter,
            embedding_provider: EmbeddingProvider,
            document_repository: DocumentRepository
    ):
        # Inyección de dependencias (SOLID)
        self.scraper = scraper
        self.splitter = splitter
        self.embedding_provider = embedding_provider
        self.repo = document_repository

    def scrape_and_save_documents(self, urls: List[str]) -> List[Dict[str, Any]]:
        """
        Ciclo completo de indexación para una lista de URLs semilla.
        Procesa documento por documento de forma secuencial y resiliente.
        """
        indexed_documents = []

        logger.info(f"=== INICIANDO PIPELINE DE INDEXACIÓN (Total: {len(urls)} URLs) ===")

        for index, url in enumerate(urls, start=1):
            logger.info(f"--- Procesando [{index}/{len(urls)}]: {url} ---")

            try:
                # FASE 1: Scraping y Limpieza de Contenido
                document_data = self.scraper.run(url)
                if not document_data:
                    logger.warning(f"URL omitida. El scraper no retornó datos para: {url}")
                    continue

                # FASE 2: Persistencia del Documento Padre
                existing_doc = self.repo.get_document_by_url(url)

                payload_doc = {
                    "url": document_data["url"],
                    "title": document_data["title"],
                    "raw_content": document_data["raw_content"],
                    "clean_content": document_data["clean_content"]
                }

                if existing_doc:
                    logger.info(f"Documento existente. Actualizando registro padre.")
                    # Si ya existía, usamos su ID actual
                    doc_record = self.repo.update_document(existing_doc["id"], payload_doc)
                    doc_id = existing_doc["id"]

                    continue
                else:
                    logger.info(f"Registrando nuevo documento padre en DB.")
                    doc_record = self.repo.insert_document(payload_doc)
                    doc_id = doc_record["id"]

                # FASE 3: Fragmentación (Chunking Híbrido)

                chunks = self.splitter.split_text(document_data["clean_content"])

                if not chunks:
                    logger.warning(f"No se generaron fragmentos para el documento: {url}")
                    continue

                # FASE 4: Vectorización en Lote Local (Embeddings)
                # Entrada: List[Dict] sin vectores -> Salida: Misma lista enriquecida con la clave 'embedding' (384 floats)
                chunks_with_vectors = self.embedding_provider.generate_embeddings_for_chunks(chunks)

                # FASE 5: Persistencia
                self.repo.insert_document_chunks(
                    document_id=doc_id,
                    chunks=chunks_with_vectors,
                    url=url
                )

                indexed_documents.append(doc_record)
                logger.info(f"✔ Indexación completa y exitosa para: {url}")

            except Exception as e:
                # Captura defensiva de errores: Si una página falla, el bucle no muere
                logger.error(f"Error catastrófico al procesar la URL {url}: {str(e)}")
                logger.info("Continuando con la siguiente URL del listado...")
                continue

        logger.info(
            f"=== PIPELINE FINALIZADO: Se indexaron exitosamente {len(indexed_documents)} de {len(urls)} documentos ===")
        return indexed_documents