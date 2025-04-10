from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.core.security import get_current_user
from app.schemas import NotificationResponse, MessageResponse
from app.models import User, Notification
from app.utils.cache import cache_data, get_cached_data, clear_cache
from app.utils.logger import log_user_action
from app.core.config import settings

router = APIRouter()

@router.get("", response_model=List[NotificationResponse])
def get_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получение уведомлений пользователя"""
    cache_key = f"user_notifications:{current_user.id}"
    cached_notifications = get_cached_data(cache_key)
    
    if cached_notifications:
        return cached_notifications
    
    notifications = db.query(Notification).filter(
        Notification.user_id == current_user.id
    ).order_by(Notification.created_at.desc()).all()
    
    result = [NotificationResponse.model_validate(notification) for notification in notifications]
    cache_data(cache_key, [notification.model_dump() for notification in result], settings.CACHE_TTL)
    
    return result

@router.post("/{notification_id}/read", response_model=MessageResponse)
def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Отметка уведомления как прочитанного"""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    if notification.is_read:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Notification already marked as read"
        )
    
    notification.is_read = True
    db.commit()
    
    # Очистка кэша
    clear_cache(f"user_notifications:{current_user.id}")
    
    log_user_action(current_user.id, "mark_notification_read", f"Notification {notification_id} marked as read")
    return {"message": "Notification marked as read"}

@router.delete("/{notification_id}")
def delete_notification(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Удаление уведомления
    """
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    db.delete(notification)
    db.commit()
    
    # Очистка кэша
    clear_cache(f"user_notifications:{current_user.id}")
    
    log_user_action(current_user.id, "delete_notification", f"Notification {notification_id} deleted")
    return {"message": "Notification deleted successfully"} 