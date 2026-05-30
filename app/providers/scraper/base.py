# app/providers/scraper/base.py

from abc import ABC, abstractmethod
import os
import json
import re
import logging

# Configuración del logger para trazabilidad (Requisito de la prueba)
logger = logging.getLogger("app.providers.scraper")


class BaseScraper(ABC):
    """
    Clase Base Abstracta que actúa como contrato (Interface) para cualquier
    estrategia de scraping en el sistema. Implementa el patrón Template Method.
    """

    def __init__(self, raw_dir: str = "data/raw", processed_dir: str = "data/processed"):
        self.raw_dir = raw_dir
        self.processed_dir = processed_dir

        os.makedirs(self.raw_dir, exist_ok=True)
        os.makedirs(self.processed_dir, exist_ok=True)

    @abstractmethod
    def fetch_page(self, url: str) -> str:
        """
        Contrato: Descarga el contenido HTML crudo de una URL específica.
        Cada subclase (banco) debe implementar su propia lógica de peticiones.
        """
        pass

    @abstractmethod
    def clean_html(self, html_content: str) -> tuple[str, str]:
        """
        Contrato: Procesa el HTML crudo, remueve el ruido (headers, footers, scripts)
        y extrae una tupla con (título_de_la_página, contenido_limpio_en_texto_o_markdown).
        """
        pass

    def _slugify(self, url: str) -> str:
        """
        Método utilitario privado para generar nombres de archivo seguros
        y sanitizados a partir de la URL.
        """
        clean_url = url.replace("https://", "").replace("http://", "").replace("www.", "")
        return re.sub(r'[^a-zA-Z0-9]', '_', clean_url)

    def save_raw(self, url: str, html_content: str) -> str:
        """
        Guarda el HTML crudo tal cual se descargó de la web en la carpeta data/raw/.
        [Requisito Obligatorio de la prueba]
        """
        filename = f"{self._slugify(url)}.html"
        filepath = os.path.join(self.raw_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_content)
        logger.info(f"Guardado archivo crudo local: {filepath}")
        return filepath

    def save_processed(self, url: str, title: str, clean_content: str) -> str:
        """
        Guarda el contenido estructurado y limpio en formato JSON en data/processed/.
        [Requisito Obligatorio de la prueba]
        """
        filename = f"{self._slugify(url)}.json"
        filepath = os.path.join(self.processed_dir, filename)

        payload = {
            "url": url,
            "title": title,
            "clean_content": clean_content
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        logger.info(f"Guardado archivo limpio local: {filepath}")
        return filepath

    def run(self, url: str) -> dict | None:
        """
        Template Method: Orquesta el esqueleto del algoritmo de scraping.
        Define los pasos fijos del flujo, delegando los detalles de implementación
        (fetch y clean) a las subclases.

        [Bonus: Manejo de errores integrado para evitar caídas del pipeline]
        """
        try:
            logger.info(f"Iniciando pipeline de scraping para: {url}")

            # Paso 1: Descargar el contenido crudo
            html_content = self.fetch_page(url)
            if not html_content:
                raise ValueError(f"No se obtuvo contenido para la URL: {url}")

            # Paso 2: Persistir el archivo crudo en local (Auditoría)
            self.save_raw(url, html_content)

            # Paso 3: Limpiar el HTML destructivamente
            title, clean_content = self.clean_html(html_content)

            # Paso 4: Persistir el archivo limpio en local
            self.save_processed(url, title, clean_content)

            logger.info(f"Pipeline de scraping finalizado con éxito para: {url}")

            # Retornamos un diccionario con la estructura idéntica a tu entidad 'documents'
            return {
                "url": url,
                "title": title,
                "raw_content": html_content,
                "clean_content": clean_content
            }

        except Exception as e:
            # Requisito Bonus: Manejo robusto de errores
            logger.error(f"Error crítico en el pipeline de scraping para la URL {url}: {str(e)}", exc_info=True)
            return None