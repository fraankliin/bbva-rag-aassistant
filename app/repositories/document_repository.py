from typing import Dict, Any, Optional
from supabase import create_client, Client
from app.core.config import settings
from app.core.logger import get_logger
from app.db.database import supabase

logger = get_logger(__name__)


class DocumentRepository:


    def __init__(self):

        self.table_name = "documents"

    def get_document_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Busca un documento en la base de datos utilizando su URL como llave de negocio.
        Sirve para validar la existencia previa y evitar duplicados (Idempotencia).
        """
        try:
            logger.info(f"Buscando documento existente en DB para la URL: {url}")
            response = (
                supabase.table(self.table_name)
                .select("*")
                .eq("url", url)
                .execute()
            )

            # Si encuentra registros, retornamos el primero
            if response.data and len(response.data) > 0:
                return response.data[0]

            return None
        except Exception as e:
            logger.error(f"Error al buscar documento por URL ({url}): {str(e)}")
            raise e

    def insert_document(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Inserta un nuevo registro en la tabla 'documents' con el contenido crudo y limpio.
        """
        try:
            logger.info(f"Insertando nuevo registro en 'documents' para: {document_data['url']}")

            response = (
                supabase.table(self.table_name)
                .insert({
                    "url": document_data["url"],
                    "title": document_data["title"],
                    "raw_content": document_data["raw_content"],
                    "clean_content": document_data["clean_content"]
                })
                .execute()
            )

            if not response.data:
                raise ValueError("No se recibieron datos de confirmación tras el INSERT en Supabase.")

            return response.data[0]
        except Exception as e:
            logger.error(f"Error crítico en el INSERT de la tabla 'documents': {str(e)}")
            raise e

    def update_document(self, document_id: str, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Actualiza un documento existente utilizando su UUID (document_id).
        Permite refrescar el contenido limpio/crudo si la página web cambió.
        """
        try:
            logger.info(f"Actualizando documento ID: {document_id} en la tabla 'documents'")

            response = (
                supabase.table(self.table_name)
                .update({
                    "title": document_data["title"],
                    "raw_content": document_data["raw_content"],
                    "clean_content": document_data["clean_content"],
                    "scraped_at": "now()"  # Le dice a Postgres que actualice el timestamp al momento actual
                })
                .eq("id", document_id)
                .execute()
            )

            if not response.data:
                raise ValueError(f"No se pudo actualizar el documento con ID: {document_id}")

            return response.data[0]
        except Exception as e:
            logger.error(f"Error crítico en el UPDATE de la tabla 'documents': {str(e)}")
            raise e



    def insert_document_chunks(self, document_id: str, chunks: list, url: str) -> bool:
        """
        Realiza una inserción masiva de los fragmentos vectorizados
        en la tabla 'document_chunks', vinculándolos al documento padre.
        """
        try:
            logger.info(f"Preparando inserción masiva de {len(chunks)} chunks para el doc ID: {document_id}")

            payload_bulk = []
            for chunk in chunks:
                payload_bulk.append({
                    "document_id": document_id,
                    "chunk_index": chunk["chunk_index"],
                    "chunk_text": chunk["chunk_text"],
                    "embedding": chunk["embedding"],  # La lista de 384 floats
                    "metadata": {
                        "source_url": url,
                        **chunk["metadata"]
                    }
                })

            # Ejecutamos un único INSERT masivo en Supabase
            supabase.table("document_chunks").insert(payload_bulk).execute()
            logger.info(f"Inserción masiva completada con éxito en 'document_chunks'.")
            return True

        except Exception as e:
            logger.error(f"Error crítico en el Bulk Insert de chunks: {str(e)}")
            raise e