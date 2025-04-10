from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.core.security import get_current_user, admin_required
from app.schemas import UserResponse, MessageResponse
from app.models import User, Task, Notification, UserRole
from app.utils.cache import clear_cache

router = APIRouter()

@router.get("/users", response_model=List[UserResponse])
async def get_all_users(
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db)
):
    """Получение списка всех пользователей (только для администраторов)"""
    return db.query(User).all()

@router.delete("/users/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Удаляет пользователя по ID.
    Только администратор может удалить любого пользователя.
    Пользователь может удалить только свой аккаунт.
    """
    if current_user.role != UserRole.ADMIN and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Удаляем все связанные данные пользователя
    db.query(Task).filter(Task.owner_id == user_id).delete()
    db.query(Notification).filter(Notification.user_id == user_id).delete()
    
    # Удаляем пользователя
    db.delete(user)
    db.commit()
    
    # Очищаем кэш
    await clear_cache(f"user:{user_id}")
    await clear_cache(f"user_tasks:{user_id}")
    
    return {"message": "User deleted successfully"} 