import logging
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer

logger = logging.getLogger("app.providers.embeddings_provider")


class EmbeddingProvider:
    """
    Proveedor encargado de la generación de vectores (embeddings) semánticos
    utilizando el modelo local y liviano 'all-MiniLM-L6-v2'.
    Corre enteramente en memoria local (CPU) dentro del contenedor.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Inicializa y carga el modelo de embeddings en la RAM del proceso.
        """
        self.model_name = model_name
        try:
            logger.info(f"Cargando el modelo de embeddings '{self.model_name}' en memoria...")

            # Instanciamos el modelo local. PyTorch detectará los hilos de tu CPU
            # de forma automática para paralelizar el cálculo numérico.
            self.model = SentenceTransformer(self.model_name, device="cpu")

            logger.info(f"Modelo '{self.model_name}' cargado exitosamente en CPU.")
        except Exception as e:
            logger.error(f"Error crítico al inicializar el modelo de embeddings: {str(e)}")
            raise e

    def generate_embeddings_for_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Toma la lista de diccionarios estructurados del TextSplitter, extrae el texto,
        calcula los vectores en un solo lote (batch) y devuelve los objetos enriquecidos.

        :param chunks: Lista de diccionarios generada por DocumentTextSplitter.
        :return: Misma lista de chunks, pero ahora cada uno incluye su clave 'embedding'.
        """
        if not chunks:
            logger.warning("Se recibió una lista vacía de chunks para vectorizar.")
            return []

        try:
            logger.info(f"Iniciando generación de embeddings en lote para {len(chunks)} chunks...")

            # 1. Extraemos únicamente los strings de texto de cada payload para pasárselos al modelo
            texts_batch = [chunk["chunk_text"] for chunk in chunks]

            # 2. El modelo procesa la lista en paralelo y calcula la matriz semántica.
            # Convertimos el output de matrices de NumPy a listas nativas de Python (List[float])
            # porque Supabase / pgvector no entiende arrays de NumPy directamente.
            vectors_matrix = self.model.encode(texts_batch, show_progress_bar=False)
            vectors_list = [vector.tolist() for vector in vectors_matrix]

            # 3. Inyectamos de forma correlativa el vector dentro de su respectivo payload de chunk
            for index, vector in enumerate(vectors_list):
                chunks[index]["embedding"] = vector

            logger.info(f"Vectores de {self.model.get_sentence_embedding_dimension()} dimensiones generados con éxito.")
            return chunks

        except Exception as e:
            logger.error(f"Error durante el procesamiento vectorial del lote: {str(e)}")
            raise e