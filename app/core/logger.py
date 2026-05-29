import logging
import os

from logging.handlers import RotatingFileHandler

from app.core.config import settings


# Crear carpeta logs si no existe
os.makedirs("logs", exist_ok=True)


LOG_FORMAT = (
    "%(asctime)s - "
    "%(name)s - "
    "%(levelname)s - "
    "%(message)s"
)


# Configuración base
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format=LOG_FORMAT
)


# Handler consola
console_handler = logging.StreamHandler()
console_handler.setFormatter(
    logging.Formatter(LOG_FORMAT)
)


# Handler archivo con rotación
file_handler = RotatingFileHandler(
    filename=settings.LOG_FILE,
    maxBytes=5 * 1024 * 1024,  # 5MB
    backupCount=3,
    encoding="utf-8"
)

file_handler.setFormatter(
    logging.Formatter(LOG_FORMAT)
)


def get_logger(name: str):

    logger = logging.getLogger(name)

    logger.setLevel(settings.LOG_LEVEL)

    # Evita handlers duplicados
    if not logger.handlers:
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

    logger.propagate = False

    return logger