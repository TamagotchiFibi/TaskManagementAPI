from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta, datetime, UTC
from jose import jwt
from app.core.config import settings
from app.db.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, Token
from app.schemas.common import MessageResponse, PasswordResetRequest, PasswordReset
from app.utils.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    check_login_attempts,
    increment_login_attempts,
    reset_login_attempts,
    get_current_user,
    admin_required
)
from app.utils.email import send_new_account_email, send_password_reset_email
from app.utils.logger import log_user_action, log_security_event
from app.utils.cache import get_redis_client
import uuid
import json
from app.models.enums import UserRole
from jose import JWTError

router = APIRouter()

@router.post("/register", response_model=UserResponse)
def register(
    user_in: UserCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Регистрация нового пользователя
    """
    print(f"Registering user: {user_in.dict()}")
    existing_user = db.query(User).filter(
        (User.username == user_in.username) | (User.email == user_in.email)
    ).first()
    if existing_user:
        print(f"User already exists: {existing_user.username}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered"
        )
    
    hashed_password = get_password_hash(user_in.password)
    user = User(
        email=user_in.email,
        username=user_in.username,
        hashed_password=hashed_password,
        is_active=True,
        role=UserRole.USER
    )
    print(f"Created user object: {user.username}")
    db.add(user)
    db.commit()
    db.refresh(user)
    print(f"User saved to database: {user.id}")
    
    # Отправка email с подтверждением
    background_tasks.add_task(
        send_new_account_email,
        email_to=user.email,
        username=user.username,
        password=user_in.password,
        background_tasks=background_tasks
    )
    
    log_user_action(user.id, "register", "New user registered")
    return user

@router.post("/token", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    redis_client = Depends(get_redis_client)
):
    """
    Вход пользователя
    """
    if not check_login_attempts(form_data.username, redis_client):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later."
        )

    user = db.query(User).filter(User.username == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        increment_login_attempts(form_data.username, redis_client)
        log_security_event("login_failed", f"Failed login attempt for user: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    reset_login_attempts(form_data.username, redis_client)
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(data={"sub": user.username})
    
    user.last_login = datetime.now(UTC)
    db.commit()
    
    log_user_action(user.id, "login", "User logged in")
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/password-reset", response_model=MessageResponse)
def request_password_reset(
    request: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    redis_client = Depends(get_redis_client)
):
    """
    Запрос на сброс пароля
    """
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    reset_token = str(uuid.uuid4())
    # Сохранение токена в кэше на 1 час
    redis_client.setex(
        f"reset_token:{reset_token}",
        3600,
        json.dumps({"user_id": user.id})
    )
    
    # Отправка email с токеном
    background_tasks.add_task(
        send_password_reset_email,
        email_to=request.email,
        token=reset_token,
        background_tasks=background_tasks
    )
    
    log_user_action(user.id, "password_reset_request", "Password reset requested")
    return {"message": "Password reset email sent"}

@router.post("/reset-password/{token}", response_model=MessageResponse)
def reset_password(
    token: str,
    request: PasswordReset,
    db: Session = Depends(get_db),
    redis_client = Depends(get_redis_client)
):
    """
    Сброс пароля по токену
    """
    # Получение данных из кэша
    token_data = redis_client.get(f"reset_token:{token}")
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token"
        )
    
    try:
        token_data = json.loads(token_data)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token format"
        )
    
    user = db.query(User).filter(User.id == token_data["user_id"]).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Обновление пароля
    user.hashed_password = get_password_hash(request.new_password)
    db.commit()
    
    # Удаление токена из кэша
    redis_client.delete(f"reset_token:{token}")
    
    log_user_action(user.id, "password_reset", "Password reset completed")
    return {"message": "Password reset successful"}

@router.delete("/users/{user_id}", response_model=dict)
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Удаление пользователя. Пользователи могут удалять только свои аккаунты,
    администраторы могут удалять любые аккаунты.
    """
    if current_user.id != user_id and current_user.role != UserRole.ADMIN:
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
    
    db.delete(user)
    db.commit()
    
    log_user_action(user.id, "delete", "User account deleted")
    return {"message": "User deleted successfully"}

@router.post("/refresh-token", response_model=Token)
async def refresh_token(
    request: dict,
    db: Session = Depends(get_db)
):
    """Обновление токена доступа с помощью refresh token"""
    try:
        payload = jwt.decode(
            request["refresh_token"],
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )
        if not payload.get("refresh"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(data={"sub": user.username})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    } 