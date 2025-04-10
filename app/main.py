# Copyright (c) 2024 Task Management API
# Licensed under the MIT License

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from app.models import Base
from app.db.database import engine
from app.core.config import settings
from app.api.v1.api import api_router

# Загрузка переменных окружения
load_dotenv()

# Создание таблиц в базе данных
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API для управления задачами с поддержкой пользователей, тегов и уведомлений",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    default_response_class=JSONResponse
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    """Корневой эндпоинт API"""
    return {"message": "Добро пожаловать в Task Management API"}