from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.core.security import get_current_user
from app.schemas import TaskCreate, TaskResponse, MessageResponse
from app.models import User, Task, Tag, UserRole, Notification
from app.utils.cache import clear_cache
from app.utils.logger import log_user_action

router = APIRouter()

@router.post("", response_model=TaskResponse)
async def create_task(
    task: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Создает новую задачу для текущего пользователя"""
    # Создаем или получаем теги
    tags = []
    for tag_name in task.tags:
        tag = db.query(Tag).filter(
            Tag.name == tag_name,
            Tag.user_id == current_user.id
        ).first()
        if not tag:
            tag = Tag(name=tag_name, user_id=current_user.id)
            db.add(tag)
    db.flush()  # Сохраняем теги в базе данных
    
    # Создаем задачу
    new_task = Task(
        text=task.text,
        priority=task.priority,
        due_date=task.due_date,
        owner_id=current_user.id
    )
    db.add(new_task)
    db.flush()  # Получаем ID задачи
    
    # Добавляем теги к задаче
    for tag_name in task.tags:
        tag = db.query(Tag).filter(
            Tag.name == tag_name,
            Tag.user_id == current_user.id
        ).first()
        new_task.tags.append(tag)
    
    # Создаем уведомление о новой задаче
    notification = Notification(
        user_id=current_user.id,
        message=f"Создана новая задача: {task.text}"
    )
    db.add(notification)
    
    db.commit()
    db.refresh(new_task)

    # Очищаем кэш уведомлений
    clear_cache(f"user_notifications:{current_user.id}")
    
    log_user_action(current_user.id, "create_task", f"Created task {new_task.id}")

    # Преобразование тегов в список строк для ответа
    response_data = {
        "id": new_task.id,
        "text": new_task.text,
        "priority": new_task.priority,
        "due_date": new_task.due_date,
        "created_at": new_task.created_at,
        "owner_id": new_task.owner_id,
        "is_completed": new_task.is_completed,
        "updated_at": new_task.updated_at,
        "tags": [tag.name for tag in new_task.tags]
    }
    return TaskResponse(**response_data)

@router.get("", response_model=List[TaskResponse])
async def get_tasks(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получает список задач текущего пользователя"""
    tasks = db.query(Task).filter(Task.owner_id == current_user.id).offset(skip).limit(limit).all()
    response_data = []
    for task in tasks:
        task_data = {
            "id": task.id,
            "text": task.text,
            "priority": task.priority,
            "due_date": task.due_date,
            "created_at": task.created_at,
            "owner_id": task.owner_id,
            "is_completed": task.is_completed,
            "updated_at": task.updated_at,
            "tags": [tag.name for tag in task.tags]
        }
        response_data.append(TaskResponse(**task_data))
    return response_data

@router.delete("/{task_id}", response_model=MessageResponse)
async def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Удаляет задачу по идентификатору"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    if task.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Удаляем все связи с тегами
    task.tags = []
    db.flush()
    
    # Удаляем задачу
    db.delete(task)
    db.commit()
    
    return {"message": "Task deleted successfully"} 