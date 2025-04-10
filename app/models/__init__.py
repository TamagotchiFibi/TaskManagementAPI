# Copyright (c) 2024 Task Management API
# Licensed under the MIT License

from app.db.database import Base
from .user import User
from .task import Task, task_tags
from .notification import Notification
from .enums import UserRole
from .tag import Tag

# Pydantic models
from pydantic import BaseModel, Field, field_validator, ConfigDict, EmailStr
from typing import List, Optional
from datetime import datetime
import re

class UserCreate(BaseModel):
    """Модель для создания пользователя"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Валидация пароля на соответствие требованиям безопасности"""
        if not re.search(r'[A-Z]', v):
            raise ValueError('Пароль должен содержать хотя бы одну заглавную букву')
        if not re.search(r'[a-z]', v):
            raise ValueError('Пароль должен содержать хотя бы одну строчную букву')
        if not re.search(r'\d', v):
            raise ValueError('Пароль должен содержать хотя бы одну цифру')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Пароль должен содержать хотя бы один специальный символ')
        return v

class UserResponse(BaseModel):
    """Модель для ответа с данными пользователя"""
    id: int
    username: str
    email: str
    role: UserRole
    is_active: bool
    email_verified: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TaskCreate(BaseModel):
    """Модель для создания задачи"""
    text: str = Field(..., min_length=1, max_length=500)
    priority: int = Field(default=3, ge=1, le=5)
    tags: List[str] = Field(default_factory=list)
    due_date: Optional[datetime] = None

class TaskResponse(BaseModel):
    """Модель для ответа с задачей"""
    id: int
    text: str
    priority: int
    is_completed: bool
    due_date: Optional[datetime]
    tags: List[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)

class NotificationResponse(BaseModel):
    """Модель для ответа с уведомлением"""
    id: int
    message: str
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

__all__ = [
    'Base', 'User', 'UserRole', 'Task', 'Tag', 'task_tags', 'Notification',
    'UserCreate', 'UserResponse', 'TaskCreate', 'TaskResponse', 'NotificationResponse'
]