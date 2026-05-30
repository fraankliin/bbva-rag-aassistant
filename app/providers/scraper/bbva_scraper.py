# app/providers/scraper/bbva_scraper.py
import re

import requests
from bs4 import BeautifulSoup, Tag
import logging
from app.providers.scraper.base import BaseScraper

logger = logging.getLogger("app.providers.scraper")


class BBVAScraper(BaseScraper):
    SPECIAL_CLASSES = [
        "microillustration__component",
        "faqscomponentv2__questions__answers__item",
        "card__body",
        "accordion__list__content",
        "linksmodule__download",
    ]

    MENU_LINK_AVG_LEN = 35



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



      # caracteres promedio por <a> en el accordion

    def _has_special_class(self, el: Tag) -> bool:



        cls = el.get("class") or []
        return any(sc in cls for sc in self.SPECIAL_CLASSES)

    def _is_inside_special(self, el: Tag) -> bool:
        """
        Retorna True si algún ancestro ya es un componente especial.
        Evita procesar los hijos de un bloque que ya fue serializado como unidad.
        """
        for parent in el.parents:
            if not isinstance(parent, Tag):
                continue
            if self._has_special_class(parent):
                return True
        return False

    def _normalize(self, text: str) -> str:
        """Colapsa espacios múltiples y elimina whitespace al inicio/fin."""
        return re.sub(r"\s+", " ", text).strip()

    def clean_html(self, html_content: str) -> tuple[str, str]:


        soup = BeautifulSoup(html_content, "html.parser")

        # ── 1. TÍTULO ─────────────────────────────────────────────────────────
        title = "Sin Título"
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            title = og_title["content"].strip()
        elif soup.title and soup.title.string:
            # Eliminar " | BBVA Colombia" y variantes del sufijo
            raw = soup.title.string.strip()
            title = re.sub(r"\s*\|\s*BBVA.*$", "", raw).strip()
        elif soup.find("h1"):
            title = soup.find("h1").get_text(separator=" ", strip=True)

        # ── 2. PURGA GLOBAL (destructiva, antes de localizar <main>) ──────────
        for tag in soup(["script", "style", "noscript", "iframe", "form"]):
            tag.decompose()

        # SVGs decorativos: icono sin texto (paths y shapes sin contenido legible)
        for svg in soup.find_all("svg"):
            if not svg.get_text(strip=True):
                svg.decompose()

        # Elementos ocultos: cookie banner y variantes
        for el in soup.find_all(class_="hidden"):
            el.decompose()

        # ── 3. ÁREA PRINCIPAL ─────────────────────────────────────────────────
        main = soup.find("main") or soup.find(id="main") or soup.find(class_="main") or soup.body
        if not main:
            return title, ""

        # Eliminar estructura institucional dentro de <main>
        for el in main.find_all(["header", "nav", "footer", "aside"]):
            el.decompose()

        # Eliminar accordions que son megamenu de navegación:
        # se distinguen porque sus <a> tienen texto muy corto (nombre de producto)
        for acc in main.find_all(class_="accordion__list__content"):
            links = acc.find_all("a")
            if links:
                avg_len = sum(len(a.get_text(strip=True)) for a in links) / len(links)
                if avg_len < self.MENU_LINK_AVG_LEN:
                    acc.decompose()

        # ── 4. CONTEXTO DE PÁGINA (metadatos de alto valor semántico) ─────────
        lines: list[str] = []
        seen: set[str] = set()  # deduplicación: tabs duplican microillustrations

        def emit(text: str, prefix: str = "") -> bool:
            """Agrega una línea normalizada si no es duplicado y tiene contenido."""
            text = self._normalize(text)
            if not text or text in seen or len(text) < 10:
                return False
            seen.add(text)
            lines.append(prefix + text)
            return True

        def emit_heading(text: str, level: int) -> bool:
            """Agrega un heading Markdown si no es duplicado."""
            text = self._normalize(text)
            if not text or text in seen:
                return False
            seen.add(text)
            prefix = "\n" + "#" * level + " "
            lines.append(prefix + text + "\n")
            return True

        # og:description — resumen del producto, excelente para el chunk de página
        og_desc = soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content"):
            desc = og_desc["content"].strip()
            if len(desc) > 30:
                lines.append(f"> {desc}\n")

        # Breadcrumb — indica la jerarquía de la página (útil en el embedding)
        bc = soup.find(attrs={"data-dl-component-name": "breadcrumb"})
        if bc:
            bc_text = bc.get_text(separator=" › ", strip=True)
            bc_text = self._normalize(bc_text)
            if bc_text:
                lines.append(f"_Sección: {bc_text}_\n")

        # ── 5. RECORRIDO SEMÁNTICO EN ORDEN DOCUMENTAL ───────────────────────
        # Iteramos .descendants para respetar el orden original del DOM.
        # Los componentes especiales se serializan como bloque; sus hijos
        # son ignorados en la rama de etiquetas estándar (via _is_inside_special).

        STANDARD_TAGS = {"h1", "h2", "h3", "h4", "p", "li", "b", "strong"}

        for el in main.descendants:
            if not isinstance(el, Tag):
                continue

            cls_list = el.get("class") or []
            cls_str = " ".join(cls_list)

            # ── Microillustration: beneficio clave con título + descripción ────
            if "microillustration__component" in cls_str:
                h = el.find(["h2", "h3", "h4", "strong", "b"])
                p_tags = el.find_all("p")
                h_text = h.get_text(separator=" ", strip=True) if h else ""
                p_text = (
                    " ".join(p.get_text(separator=" ", strip=True) for p in p_tags)
                    if p_tags
                    else el.get_text(separator=" ", strip=True)
                )
                if h_text:
                    emit_heading(h_text, 3)
                emit(p_text)
                continue

            # ── FAQ: par pregunta/respuesta — chunk natural para RAG ──────────
            # Estructura AEM de BBVA:
            #   <p class="faqquestionanswer__title">  → pregunta
            #   <div class="faqquestionanswer__text">  → respuesta
            if "faqscomponentv2__questions__answers__item" in cls_str:
                q_el = el.find(class_="faqquestionanswer__title")
                ans_el = el.find(class_="faqquestionanswer__text")
                q_text = q_el.get_text(separator=" ", strip=True) if q_el else ""
                ans_text = (
                    self._normalize(ans_el.get_text(separator=" ", strip=True))
                    if ans_el
                    else self._normalize(el.get_text(separator=" ", strip=True))
                )
                if q_text and q_text not in seen:
                    seen.add(q_text)
                    lines.append(f"\n**P: {q_text}**")
                if ans_text:
                    emit(ans_text, "R: ")
                continue

            # ── Card body: descripción de productos relacionados ───────────────
            if "card__body" in cls_str:
                text = el.get_text(separator=" ", strip=True)
                if len(text) > 30:
                    emit(text, "- ")
                continue

            # ── Accordion de contenido (supervivientes = T&C, requisitos…) ────
            if "accordion__list__content" in cls_str:
                text = el.get_text(separator=" ", strip=True)
                if len(text) > 60:
                    emit(text)
                continue

            # ── Links de descarga: documentos disponibles (PDF, formularios) ──
            if "linksmodule__download" in cls_str:
                text = el.get_text(separator=" ", strip=True)
                emit(text, "- Documento: ")
                continue

            # ── Etiquetas HTML estándar ───────────────────────────────────────
            # Solo se procesan si NO son descendientes de un componente especial
            # (evita duplicar texto que ya fue serializado por el bloque padre).
            if el.name in STANDARD_TAGS and not self._is_inside_special(el):
                # Usar separator=" " para que inline elements (<a>,<b>) no se peguen
                text = el.get_text(separator=" ", strip=True)

                if el.name == "h1":
                    emit_heading(text, 1)
                elif el.name == "h2":
                    emit_heading(text, 2)
                elif el.name == "h3":
                    emit_heading(text, 3)
                elif el.name == "h4":
                    emit_heading(text, 4)
                elif el.name == "li":
                    if len(text) > 15:
                        emit(text, "- ")
                elif el.name in ("p", "b", "strong"):
                    # Filtrar CTAs y textos operativos cortos
                    if len(text) > 15:
                        emit(text)

        clean_text = "\n".join(lines).strip()
        return title, clean_text

