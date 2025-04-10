from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func, Enum, Boolean
from sqlalchemy.orm import relationship
from app.db.database import Base
from app.models.enums import UserRole

class User(Base):
    """Модель пользователя"""
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(Enum(UserRole), default=UserRole.USER)
    is_active = Column(Boolean, default=True)
    email_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True))
    tasks = relationship("Task", back_populates="owner", cascade="all, delete-orphan")
    tags = relationship("Tag", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan") 