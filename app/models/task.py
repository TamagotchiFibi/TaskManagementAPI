from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func, Boolean, Table, CheckConstraint
from sqlalchemy.orm import relationship, validates
from app.db.database import Base

# Связь многие-ко-многим между задачами и тегами
task_tags = Table(
    'task_tags',
    Base.metadata,
    Column('task_id', Integer, ForeignKey('tasks.id', ondelete='CASCADE'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True)
)

class Task(Base):
    """Модель задачи"""
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    text = Column(String, nullable=False)
    priority = Column(Integer, default=1)
    is_completed = Column(Boolean, default=False)
    due_date = Column(DateTime, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="tasks")
    tags = relationship("Tag", secondary=task_tags, back_populates="tasks")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    __table_args__ = (
        CheckConstraint('priority >= 1 AND priority <= 5', name='check_priority_range'),
    )

    @validates('priority')
    def validate_priority(self, key, priority):
        if not 1 <= priority <= 5:
            raise ValueError("Priority must be between 1 and 5")
        return priority 