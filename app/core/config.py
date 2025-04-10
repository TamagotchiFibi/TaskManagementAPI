import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import List, Optional, Any
import logging
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """Настройки приложения"""
    
    # Основные настройки
    PROJECT_NAME: str = "Task Management API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    TESTING: bool = False
    
    # Настройки базы данных
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./app.db")
    TEST_DATABASE_URL: str = os.getenv("TEST_DATABASE_URL", "sqlite:///./test.db")
    
    # Настройки Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # Настройки безопасности
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Настройки CORS
    BACKEND_CORS_ORIGINS: List[str] = ["*"]
    
    # Настройки email
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    
    # Настройки безопасности
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_TIME: int = 15  # в минутах
    RATE_LIMIT: int = 100  # запросов в минуту
    
    # Email
    SMTP_TLS: bool = True
    EMAILS_FROM_EMAIL: str = os.getenv("EMAILS_FROM_EMAIL", "noreply@example.com")
    EMAILS_FROM_NAME: str = os.getenv("EMAILS_FROM_NAME", "Task Management API")
    
    # Кэширование
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
    REDIS_DB: int = int(os.getenv("REDIS_DB", 0))
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", 300))
    
    # Логирование
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "logs/app.log")
    
    # API документация
    OPENAPI_URL: str = "/openapi.json"
    DOCS_URL: str = "/docs"
    REDOC_URL: str = "/redoc"
    
    # Поля для базы данных
    engine: Any = None
    SessionLocal: Any = None
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Создаем движок базы данных
        database_url = self.TEST_DATABASE_URL if self.TESTING else self.DATABASE_URL
        self.engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False} if database_url.startswith("sqlite") else {}
        )
        # Создаем сессию
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"

# Создаем экземпляр настроек
settings = Settings()

# Настройка логирования
if settings.LOG_FILE:
    log_dir = Path(settings.LOG_FILE).parent
    log_dir.mkdir(parents=True, exist_ok=True)
    
    file_handler = logging.FileHandler(settings.LOG_FILE)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)

logger.setLevel(settings.LOG_LEVEL) 