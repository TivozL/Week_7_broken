import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.settings import settings

def setup_logging():

    log_dir = Path(settings.log_file_path).parent   #папка из настроек
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger()    #инициализация
    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    if logger.hasHandlers():
        logger.handlers.clear()

    formatter = logging.Formatter(      #форматирование
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    file_handler = RotatingFileHandler(
        settings.log_file_path,
        maxBytes=10_485_760, #до 10 мб
        encoding="utf-8"
    )

    file_handler.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)      #получить логгер для конкретного модуля


app_logger = get_logger("app")      #основные логгеры приложения
db_logger = get_logger("app.database")
service_logger = get_logger("app.services")
repos_logger = get_logger("app.repositories")
router_logger = get_logger("app.routers")