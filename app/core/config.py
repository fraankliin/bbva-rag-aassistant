from dataclasses import Field
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "BBVA RAG Assistant"
    APP_VERSION: str = "1.0.0"

    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"

    SUPABASE_URL: str
    SUPABASE_KEY: str

    GEMINI_API_KEY: str


    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

settings = Settings()
