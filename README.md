# BBVA RAG Assistant - Ecosistema de Recuperación Aumentada por Generación

Este proyecto implementa una solución para un asistente conversacional automatizado con capacidades de **Retrieval-Augmented Generation (RAG)**. El sistema es capaz de realizar Web Scraping sobre el portal institucional de BBVA Colombia, preprocesar, fragmentar de forma híbrida y vectorizar la información persistiendo los embeddings en una base de datos vectorial nativa, exponiendo tanto una API robusta en FastAPI como un panel de analíticas y chat conversacional interactivo.

---

## Requisitos Previos

Antes de realizar el despliegue, asegúrese de contar con las siguientes herramientas instaladas en su máquina local:
* **Docker Desktop**
* **Git**
* Una API Key de **Google AI Studio** (Modelo Gemini).

---

## Instrucciones de Despliegue Paso a Paso

Siga estos comandos secuenciales para clonar ambos repositorios independientes en una única carpeta raíz local y levantar todo el ecosistema multi-contenedor de manera automatizada:

```bash
# 1. Crear y acceder a la carpeta contenedora general
mkdir bbva-assistant && cd bbva-assistant

# 2. Clonar el repositorio del Backend (FastAPI)
git clone https://github.com/fraankliin/bbva-rag-aassistant.git

# 3. Clonar el repositorio del Frontend (Nginx Web Server)
git clone https://github.com/fraankliin/front-assistant-bbva.git

# 4. Acceder al directorio raíz del Backend donde reside el orquestador
cd bbva-rag-assistant

# 5. Configurar las Variables de Entorno obligatorias (.env) en bva-rag-assistant
cat <<EOF > .env
SUPABASE_URL=tu_url_de_supabase
SUPABASE_KEY=tu_api_key_de_supabase
GEMINI_API_KEY=tu_api_key_de_gemini
EOF

# 6. Levantar todo el ecosistema con Docker Compose
docker-compose up --build -d
```

## ¿Qué ocurre internamente tras ejecutar el comando?
Docker Compose leerá los contextos de forma relativa. Construirá la capa del backend instalando las dependencias de Python, expondrá la API en el puerto 8000 e iniciará inmediatamente su manejador asíncrono lifespan ejecutando el Web Scraper de fondo para poblar Supabase. Paralelamente, empaquetará la interfaz Vanilla mediante un servidor Nginx Alpine invertido expuesto en el puerto 5500.


---

## Cómo Usar la Interfaz Conversacional y Analíticas

Una vez que todos los contenedores reporten un estado saludable (`healthy`), interactúe con el ecosistema a través del navegador:

1. **Autenticación e Interfaz de Usuario:** Ingrese a `http://localhost:5500/login.html` en su navegador para registrarse, iniciar sesión y acceder al panel unificado del chat conversacional (`chat.html`) y búsqueda semántica (`search.html`).
2. **Consola de Métricas y Analíticas:** Navegue a `http://localhost:5500/pages/analytics.html` para consultar el módulo dedicado a recorrer el histórico de conversaciones, permitiendo extraer métricas y valores de impacto sobre las interacciones de los usuarios.
3. **Sandbox Técnico (Swagger UI):** Para probar los endpoints, esquemas de entrada/salida y simular solicitudes de forma aislada, acceda a la documentación nativa e interactiva de FastAPI en: `http://localhost:8000/docs`.

---

## Patrones de Diseño Utilizados

El backend del sistema fue estructurado bajo una arquitectura limpia y desacoplada utilizando patrones de diseño de software específicos para garantizar extensibilidad y cumplimiento de ingeniería:

* **Pattern Provider / Strategy (Estructural / Comportamental):** Aplicado estrictamente en la capa de servicios cognitivos (`app/providers/`). Las abstracciones base `base_llm.py` y `base.py` de scraping definen contratos estrictos. Esto permite alternar entre proveedores de LLM (como Gemini) o diferentes estrategias de Scrapers sin alterar la lógica de negocio subyacente.
* **Repository Pattern (Estructural):** Implementado en `app/repositories/` (ej. `analytics_repository.py`, `document_repository.py`). Toda la manipulación de datos y persistencia directa con el SDK de Supabase se encapsula en esta capa, aislando completamente las rutas de la API de la infraestructura de almacenamiento.
* **Dependency Injection (Estructural):** Utilizado de manera extensiva en las rutas de FastAPI a través de su sistema nativo `Depends`. Las instancias de los servicios de orquestación, scraping y repositorios se inyectan dinámicamente en los endpoints, facilitando las pruebas unitarias y el desacoplamiento de componentes.

---

## Stack Tecnológico Elegido y Justificación

| Tecnología | Rol en el Ecosistema | Justificación Técnica |
| :--- | :--- | :--- |
| **FastAPI** | Framework Backend Async | Ofrece manejo nativo de asincronía (`async/await`), alta velocidad de ejecución y validación estricta de tipos de datos mediante Pydantic. |
| **Supabase (PostgreSQL + pgvector)** | Base de Datos Vectorial | Permite almacenar metadatos relacionales tradicionales y vectores embebidos en un mismo motor transaccional mediante la extensión `pgvector`, ejecutando búsquedas semánticas eficientes. |
| **RPC (Remote Procedure Calls)** | Mecanismo de Búsqueda Vectorial | Permite ejecutar la lógica matemática de comparación de vectores (`cosine_similarity`) directamente en el servidor de la base de datos, optimizando el rendimiento. |
| **SentenceTransformers (`all-MiniLM-L6-v2`)** | Generador de Embeddings Local | Modelo denso de 384 dimensiones ejecutado de manera local en CPU. Ofrece un balance óptimo entre latencia de procesamiento y precisión semántica sin costo de infraestructura. |
| **Gemini 1.5 Flash / Lite** | Modelo de Lenguaje de Gran Escala | Seleccionado por su ventana de contexto extendida y su baja latencia para respuestas conversacionales rápidas y eficaces. |
| **HTML5 / CSS3 / JavaScript (Vanilla)** | Interfaz de Usuario Front-end | Arquitectura nativa sin frameworks pesados, garantizando un renderizado instantáneo en el navegador del cliente. |
| **Nginx (Alpine Image)** | Servidor de Archivos Estáticos | Servidor HTTP de grado producción extremadamente ligero utilizado para servir de forma segura el frontend y unificar el flujo web. |
| **Docker & Docker Compose** | Contenerización y Orquestación | Garantiza la portabilidad absoluta del sistema, encapsulando dependencias para que funcione con un solo comando. |

---

##  Limitaciones Conocidas y Decisiones de Diseño

* **Ejecución Asíncrona con Bloqueo de CPU en Embeddings:** La librería `SentenceTransformers` es síncrona y consume ciclos intensivos de CPU al generar embeddings. Para evitar congelar el bucle de eventos principal de FastAPI (`Event Loop`) durante la fase de indexación masiva del scraper, se tomó la decisión de diseño de delegar la vectorización a hilos secundarios aislados utilizando de forma explícita el método `asyncio.to_thread`.
* **Idempotencia de Chunks en el Pipeline RAG:** Al reactivarse el scraper mediante el inicio del contenedor, se corría el riesgo de duplicar vectores hijos en la base de datos. Se diseñó una estrategia idempotente de limpieza automática que ejecuta un borrado transaccional de los fragmentos antiguos (`delete_chunks_by_document_id`) antes de insertar los nuevos vectores generados, manteniendo la consistencia.
* **Políticas de CORS y Aislamiento de Entorno:** El JavaScript del frontend se ejecuta en el navegador del cliente final, por ende consume la API apuntando directamente al puerto expuesto `localhost:8000`, mientras que el contenedor de Nginx opera de manera aislada sirviendo el estático.

---

## Futuras Mejoras del Sistema

* **Estrategia Avanzada de Recuperación (Reranking):** Implementar un nodo secundario de reordenamiento utilizando un modelo de Cross-Encoder (como `bge-reranker`) posterior a la búsqueda semántica en la base de datos vectorial para recalcular la relevancia de los candidatos recuperados antes de inyectarlos en el prompt del LLM.
* **Evolución del Chunking Híbrido:** Migrar el divisor de texto actual hacia una estrategia de *Parent-Child Chunking* o fragmentación semántica basada en el cambio de oraciones, de forma que se extraigan segmentos pequeños y específicos para indexar vectores pero se le pase un contexto más amplio al modelo generativo.
* **Mapeo Avanzado de Rutas Dinámicas en el Scraper:** Añadir un resolvedor jerárquico que procese estructuras complejas de tablas y archivos adjuntos (PDFs) comunes en portales bancarios institucionales, extrayendo metadatos detallados de auditoría.
