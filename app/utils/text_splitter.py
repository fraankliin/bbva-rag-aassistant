
import logging
from typing import List, Dict, Any
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

logger = logging.getLogger("app.utils.text_splitter")


class DocumentTextSplitter:
    """
    Componente encargado de fragmentar (chunkear) el contenido limpio en Markdown
    de los documentos utilizando una estrategia híbrida estructural y lineal.
    """

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap


        self.headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
        ]
        self.markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=self.headers_to_split_on,
            strip_headers=False
        )

        self.character_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", " ", ""]  # Intenta romper en párrafos, luego líneas, luego espacios
        )

    def split_text(self, clean_content: str) -> List[Dict[str, Any]]:

        if not clean_content or not clean_content.strip():
            logger.warning("Se recibió un contenido vacío para fragmentar.")
            return []

        try:
            logger.info("Iniciando división estructural por headers de Markdown...")
            # Fase 1: Dividir por la estructura de títulos de la página
            markdown_sections = self.markdown_splitter.split_text(clean_content)

            final_chunks = []
            chunk_index = 0

            logger.info(f"Fase 1 completada. Se generaron {len(markdown_sections)} secciones iniciales.")
            logger.info("Iniciando Fase 2: Sub-división recursiva por caracteres...")

            # Fase 2: Iterar sobre cada sección estructural y subdividir si excede el tamaño límite
            for section in markdown_sections:
                # El splitter de markdown extrae el texto y guarda los headers detectados en .metadata
                text_to_split = section.page_content
                structural_metadata = section.metadata

                # Subdividimos recursivamente el texto de la sección
                sub_chunks = self.character_splitter.split_text(text_to_split)

                for sub_chunk_text in sub_chunks:
                    chunk_payload = {
                        "chunk_index": chunk_index,
                        "chunk_text": sub_chunk_text,
                        "metadata": {
                            "structural_headers": structural_metadata,
                            "char_length": len(sub_chunk_text)
                        }
                    }
                    final_chunks.append(chunk_payload)
                    chunk_index += 1

            logger.info(f"Fragmentación finalizada con éxito. Total de chunks generados: {len(final_chunks)}")
            return final_chunks

        except Exception as e:
            logger.error(f"Error crítico durante el proceso de fragmentación (chunking): {str(e)}")
            raise e