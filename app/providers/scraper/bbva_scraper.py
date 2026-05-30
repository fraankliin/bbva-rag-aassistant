# app/providers/scraper/bbva_scraper.py

import requests
from bs4 import BeautifulSoup
import logging
from app.providers.scraper.base import BaseScraper

logger = logging.getLogger("app.providers.scraper")


class BBVAScraper(BaseScraper):


    def fetch_page(self, url: str) -> str:
        """
        Realiza la petición HTTP GET para obtener el HTML de la página del banco.
        [Bonus: Manejo de encabezados para evitar bloqueos]
        """
        # Encabezados que simulan un navegador real moderno
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3",
            "Cache-Control": "max-age=0",
            "Connection": "keep-alive"
        }

        logger.info(f"Enviando petición HTTP a: {url}")

        # Agregamos un timeout prudente para evitar que Docker se quede congelado
        response = requests.get(url, headers=headers, timeout=15)

        # Levanta una excepción HTTPError si el código no es 200 (ej. 404, 500)
        response.raise_for_status()

        # Forzar la codificación correcta para evitar caracteres extraños (tildes, eñes colombianas)
        response.encoding = 'utf-8'

        return response.text

    def clean_html(self, html_content: str) -> tuple[str, str]:
        """
        Analiza el HTML crudo, remueve la estructura institucional innecesaria
        y devuelve el título y el contenido formateado semánticamente en Markdown.
        """
        soup = BeautifulSoup(html_content, "html.parser")

        # 1. Obtener el título de la página
        title = "Sin Título"
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
        elif soup.find("h1"):
            title = soup.find("h1").get_text(strip=True)

        # 2. Purgar etiquetas ruidosas (Eliminación destructiva de basura)
        # Esto limpia menús, pies de página, formularios de login y scripts de analítica
        tags_to_drop = [
            "script", "style", "header", "footer", "nav", "aside",
            "form", "iframe", "noscript", ".header", ".footer", ".navigation"
        ]
        for tag in soup(tags_to_drop):
            tag.extract()

        # 3. Identificar el área de contenido principal (Heurística)
        # Los sitios modernos de BBVA suelen usar la etiqueta semántica <main>
        main_area = soup.find("main") or soup.find(id="main") or soup.find(class_="main") or soup.body

        if not main_area:
            return title, ""

        # 4. Extraer el contenido de manera jerárquica y convertir a Markdown simple
        # El formato Markdown ayuda al RAG a entender la relevancia de los títulos
        markdown_lines = []

        # Recorremos solo las etiquetas que aportan valor de texto real
        for element in main_area.find_all(["h1", "h2", "h3", "h4", "p", "li"]):
            text = element.get_text(strip=True)
            if not text:
                continue

            # Validamos el tipo de etiqueta para estructurar el Markdown
            if element.name == "h1":
                markdown_lines.append(f"\n# {text}\n")
            elif element.name == "h2":
                markdown_lines.append(f"\n## {text}\n")
            elif element.name == "h3":
                markdown_lines.append(f"\n### {text}\n")
            elif element.name == "h4":
                markdown_lines.append(f"\n#### {text}\n")
            elif element.name == "li":
                markdown_lines.append(f"- {text}")
            elif element.name == "p":
                # Evitamos guardar textos excesivamente cortos u operativos (ej. "Compartir", "Saber más")
                if len(text) > 15:
                    markdown_lines.append(text)

        # Unimos las líneas limpias con saltos de página normales
        clean_text = "\n".join(markdown_lines).strip()

        return title, clean_text