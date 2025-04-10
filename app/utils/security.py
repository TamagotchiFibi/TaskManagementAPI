from datetime import datetime, timedelta, UTC
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.database import get_db
from app.models import User, UserRole
from fastapi.security import HTTPBearer
from fastapi import Request
from app.utils.cache import get_redis_client

# Контекст для хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# Схема OAuth2 для аутентификации
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/token")
# Схема HTTP Bearer для дополнительной безопасности
security = HTTPBearer()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверяет соответствие пароля его хешу"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Создает хеш пароля"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Создает JWT токен доступа с указанным сроком действия"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict) -> str:
    """Создает JWT токен обновления"""
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "refresh": True})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def check_login_attempts(username: str, redis_client = Depends(get_redis_client)) -> bool:
    """Проверяет количество попыток входа для пользователя"""
    key = f"login_attempts:{username}"
    attempts = redis_client.get(key)
    if attempts and int(attempts) >= settings.MAX_LOGIN_ATTEMPTS:
        return False
    return True

def increment_login_attempts(username: str, redis_client = Depends(get_redis_client)):
    """Увеличивает счетчик попыток входа для пользователя"""
    key = f"login_attempts:{username}"
    redis_client.incr(key)
    redis_client.expire(key, settings.LOCKOUT_TIME * 60)

def reset_login_attempts(username: str, redis_client = Depends(get_redis_client)):
    """Сбрасывает счетчик попыток входа для пользователя"""
    key = f"login_attempts:{username}"
    redis_client.delete(key)

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Получает текущего пользователя по JWT токену"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось проверить учетные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

def check_admin_role(user: User) -> bool:
    """Проверяет, является ли пользователь администратором"""
    if not user or not isinstance(user, User):
        return False
    return user.role == UserRole.ADMIN

def admin_required():
    """Создает зависимость для проверки прав администратора"""
    def admin_check(current_user: User = Depends(get_current_user)) -> User:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Не авторизован"
            )
        if not check_admin_role(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав для выполнения операции"
            )
        return current_user
    return admin_check

# Middleware для защиты от атак
async def security_middleware(request: Request, call_next):
    # Защита от XSS
    request.headers["X-XSS-Protection"] = "1; mode=block"
    request.headers["X-Content-Type-Options"] = "nosniff"
    request.headers["X-Frame-Options"] = "DENY"
    
    # Защита от CSRF
    if request.method in ["POST", "PUT", "DELETE"]:
        csrf_token = request.headers.get("X-CSRF-Token")
        if not csrf_token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Отсутствует CSRF токен"
            )
    
    # Rate limiting
    redis_client = get_redis_client()
    ip = request.client.host
    key = f"rate_limit:{ip}"
    current = redis_client.get(key)
    if current and int(current) > settings.RATE_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Слишком много запросов"
        )
    redis_client.incr(key)
    redis_client.expire(key, 60)
    
    response = await call_next(request)
    return response 