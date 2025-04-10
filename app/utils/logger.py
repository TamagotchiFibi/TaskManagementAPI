import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from app.core.config import settings
import sys
from typing import Optional

def setup_logger():
    """Настраивает логгер для приложения"""
    
    # Создание директории для логов, если она не существует
    log_dir = os.path.dirname(settings.LOG_FILE)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Создание форматтера
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Настройка файлового обработчика
    file_handler = RotatingFileHandler(
        settings.LOG_FILE,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    
    # Настройка консольного обработчика
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Получение корневого логгера
    logger = logging.getLogger()
    logger.setLevel(settings.LOG_LEVEL)
    
    # Добавление обработчиков
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# Инициализация логгера
logger = setup_logger()

def log_user_action(user_id: int, action: str, details: str = "") -> None:
    """
    Логирование действий пользователя
    """
    logger = logging.getLogger("user_actions")
    logger.info(f"User {user_id} - {action} - {details}")

def log_security_event(event_type: str, details: str) -> None:
    """
    Логирование событий безопасности
    """
    logger = logging.getLogger("security")
    logger.warning(f"Security event: {event_type} - {details}")

def log_api_request(
    method: str,
    path: str,
    status_code: int,
    user_id: Optional[int] = None,
    duration: float = 0.0
) -> None:
    """
    Логирование API запросов
    """
    logger = logging.getLogger("api")
    user_info = f"user_id={user_id}" if user_id else "anonymous"
    logger.info(
        f"{method} {path} - {status_code} - {user_info} - {duration:.2f}s"
    ) 