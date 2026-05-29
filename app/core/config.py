from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "BBVA RAG Assistant"
    APP_VERSION: str = "1.0.0"

settings = Settings()
