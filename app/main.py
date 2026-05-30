from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes.health import router as health_router
from app.api.routes.internal_users import router as internal_users_router
from app.api.routes.scraper import router as scraper_router
from app.api.routes.search import router as search_router
from app.api.routes.chat import router as chat_router
from app.api.routes.analytics import router as analytics_router


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
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
