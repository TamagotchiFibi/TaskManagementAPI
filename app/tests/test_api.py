import pytest
from fastapi.testclient import TestClient
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime, UTC
from app.utils.cache import get_redis_client
from httpx import AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_session
import uuid
import time
import json

from app.main import app
from app.models import User, Notification, UserRole, Task, Tag
from app.core.config import settings
from app.core.security import get_password_hash

# Установка тестового режима
settings.TESTING = True

# Загрузка тестового окружения
env_path = Path(__file__).parent.parent.parent / ".env.test"
load_dotenv(env_path)

# Фикстуры
@pytest.fixture(autouse=True)
def clear_redis(redis_client):
    """Очищает Redis перед каждым тестом"""
    redis_client.flushall()
    yield
    redis_client.flushall()

@pytest.fixture
def test_user_data():
    return {
        "username": f"testuser_{uuid.uuid4().hex[:8]}",
        "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
        "password": "Test1234!",
        "role": "user"
    }

@pytest.fixture
def registered_user(client, test_user_data):
    response = client.post(
        f"{settings.API_V1_STR}/register",
        json=test_user_data
    )
    assert response.status_code == 200
    return response.json()

@pytest.fixture
def auth_headers(client, test_user_data, registered_user):
    response = client.post(
        f"{settings.API_V1_STR}/token",
        data={
            "username": test_user_data["username"],
            "password": test_user_data["password"]
        }
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def admin_user_data():
    return {
        "username": "admin123",
        "email": "admin@example.com",
        "password": "AdminPassword123!@#"
    }

@pytest.fixture
def registered_admin(client, admin_user_data, db_session):
    # Create admin user directly in the database
    hashed_password = get_password_hash(admin_user_data["password"])
    admin = User(
        email=admin_user_data["email"],
        username=admin_user_data["username"],
        hashed_password=hashed_password,
        is_active=True,
        role=UserRole.ADMIN
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    return admin

@pytest.fixture
def admin_auth_headers(client, admin_user_data, registered_admin):
    response = client.post(
        f"{settings.API_V1_STR}/token",
        data={
            "username": admin_user_data["username"],
            "password": admin_user_data["password"]
        }
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def test_notification(db_session, registered_user):
    """Создает тестовое уведомление"""
    notification = Notification(
        message="Test notification message",
        user_id=registered_user["id"],
        is_read=False
    )
    db_session.add(notification)
    db_session.commit()
    db_session.refresh(notification)
    return notification

# Тесты
def test_register_user(client, test_user_data):
    """Test user registration with valid data"""
    response = client.post(
        f"{settings.API_V1_STR}/register",
        json=test_user_data
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert data["username"] == test_user_data["username"]
    assert data["email"] == test_user_data["email"]
    assert "created_at" in data
    assert data["created_at"] is not None
    assert data["role"] == "user"
    assert data["is_active"] is True

def test_register_user_invalid_password(client, test_user_data):
    """Test user registration with invalid password"""
    invalid_data = test_user_data.copy()
    invalid_data["password"] = "weak"  # Too short
    response = client.post(
        f"{settings.API_V1_STR}/register",
        json=invalid_data
    )
    assert response.status_code == 422
    assert "password" in response.json()["detail"][0]["loc"]
    
    invalid_data["password"] = "password123"  # No uppercase
    response = client.post(
        f"{settings.API_V1_STR}/register",
        json=invalid_data
    )
    assert response.status_code == 422
    assert "password" in response.json()["detail"][0]["loc"]
    
    invalid_data["password"] = "PASSWORD123"  # No lowercase
    response = client.post(
        f"{settings.API_V1_STR}/register",
        json=invalid_data
    )
    assert response.status_code == 422
    assert "password" in response.json()["detail"][0]["loc"]
    
    invalid_data["password"] = "Password"  # No numbers
    response = client.post(
        f"{settings.API_V1_STR}/register",
        json=invalid_data
    )
    assert response.status_code == 422
    assert "password" in response.json()["detail"][0]["loc"]
    
    invalid_data["password"] = "Password123"  # No special characters
    response = client.post(
        f"{settings.API_V1_STR}/register",
        json=invalid_data
    )
    assert response.status_code == 422
    assert "password" in response.json()["detail"][0]["loc"]

def test_register_user_invalid_email(client, test_user_data):
    """Test user registration with invalid email"""
    invalid_data = test_user_data.copy()
    invalid_data["email"] = "invalid-email"
    response = client.post(
        f"{settings.API_V1_STR}/register",
        json=invalid_data
    )
    assert response.status_code == 422
    assert "email" in response.json()["detail"][0]["loc"]

def test_register_user_invalid_username(client, test_user_data):
    """Test user registration with invalid username"""
    invalid_data = test_user_data.copy()
    invalid_data["username"] = "a"  # Too short
    response = client.post(
        f"{settings.API_V1_STR}/register",
        json=invalid_data
    )
    assert response.status_code == 422
    assert "username" in response.json()["detail"][0]["loc"]
    
    invalid_data["username"] = "a" * 51  # Too long
    response = client.post(
        f"{settings.API_V1_STR}/register",
        json=invalid_data
    )
    assert response.status_code == 422
    assert "username" in response.json()["detail"][0]["loc"]
    
    invalid_data["username"] = "test user"  # Contains space
    response = client.post(
        f"{settings.API_V1_STR}/register",
        json=invalid_data
    )
    assert response.status_code == 422
    assert "username" in response.json()["detail"][0]["loc"]

def test_register_existing_user(client, test_user_data):
    """Тест регистрации существующего пользователя"""
    # Сначала регистрируем пользователя
    response = client.post(
        f"{settings.API_V1_STR}/register",
        json=test_user_data
    )
    assert response.status_code == 200
    
    # Пытаемся зарегистрировать того же пользователя снова
    response = client.post(
        f"{settings.API_V1_STR}/register",
        json=test_user_data
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Username or email already registered"

def test_login_success(client, test_user_data, registered_user):
    """Test successful login"""
    response = client.post(
        f"{settings.API_V1_STR}/token",
        data={
            "username": test_user_data["username"],
            "password": test_user_data["password"]
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    
    # Получение информации о пользователе с токеном
    get_response = client.get(
        f"{settings.API_V1_STR}/users/me",
        headers={"Authorization": f"Bearer {data['access_token']}"}
    )
    assert get_response.status_code == 200
    user_data = get_response.json()
    assert user_data["username"] == test_user_data["username"]
    assert user_data["email"] == test_user_data["email"]
    
    # Verify that refresh token is valid
    refresh_response = client.post(
        f"{settings.API_V1_STR}/refresh-token",
        json={"refresh_token": data["refresh_token"]}
    )
    assert refresh_response.status_code == 200
    refresh_data = refresh_response.json()
    assert "access_token" in refresh_data
    assert "refresh_token" in refresh_data
    assert refresh_data["token_type"] == "bearer"
    
    # Verify that new access token is valid
    new_headers = {"Authorization": f"Bearer {refresh_data['access_token']}"}
    new_get_response = client.get(
        f"{settings.API_V1_STR}/users/me",
        headers=new_headers
    )
    assert new_get_response.status_code == 200
    new_user_data = new_get_response.json()
    assert new_user_data["username"] == test_user_data["username"]
    assert new_user_data["email"] == test_user_data["email"]

def test_login_wrong_password(client, test_user_data, registered_user):
    """Test login with wrong password"""
    # Try to login with wrong password
    response = client.post(
        f"{settings.API_V1_STR}/token",
        data={
            "username": test_user_data["username"],
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"
    
    # Try to login with wrong username
    response = client.post(
        f"{settings.API_V1_STR}/token",
        data={
            "username": "wronguser",
            "password": test_user_data["password"]
        }
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"
    
    # Try to login with empty credentials
    response = client.post(
        f"{settings.API_V1_STR}/token",
        data={
            "username": "",
            "password": test_user_data["password"]
        }
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"

def test_create_task(client, auth_headers, registered_user):
    """Test task creation"""
    # Try to create task without authorization
    task_data = {
        "text": "Test task",
        "priority": 1,
        "tags": ["test", "important"],
        "created_at": datetime.now(UTC).isoformat()
    }
    response = client.post(
        f"{settings.API_V1_STR}/tasks",
        json=task_data
    )
    assert response.status_code == 401
    
    # Try to create task with empty text
    empty_text_data = task_data.copy()
    empty_text_data["text"] = ""
    response = client.post(
        f"{settings.API_V1_STR}/tasks",
        json=empty_text_data,
        headers=auth_headers
    )
    assert response.status_code == 422
    assert "text" in response.json()["detail"][0]["loc"]
    
    # Try to create task with invalid priority
    invalid_priority_data = task_data.copy()
    invalid_priority_data["priority"] = 0
    response = client.post(
        f"{settings.API_V1_STR}/tasks",
        json=invalid_priority_data,
        headers=auth_headers
    )
    assert response.status_code == 422
    assert "priority" in response.json()["detail"][0]["loc"]
    
    invalid_priority_data["priority"] = 6
    response = client.post(
        f"{settings.API_V1_STR}/tasks",
        json=invalid_priority_data,
        headers=auth_headers
    )
    assert response.status_code == 422
    assert "priority" in response.json()["detail"][0]["loc"]
    
    # Create task with valid data
    response = client.post(
        f"{settings.API_V1_STR}/tasks",
        json=task_data,
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert data["text"] == task_data["text"]
    assert data["priority"] == task_data["priority"]
    assert set(data["tags"]) == set(task_data["tags"])
    assert "id" in data
    assert "created_at" in data
    assert data["created_at"] is not None
    assert data["owner_id"] == registered_user["id"]

async def test_get_tasks(client, registered_user, auth_headers):
    """Test getting tasks with various filters and sorting"""
    # Create test tasks
    tasks_data = [
        {
            "text": "Task 1",
            "priority": 1,
            "tags": ["test"],
            "created_at": datetime.now(UTC).isoformat()
        },
        {
            "text": "Task 2",
            "priority": 3,
            "tags": ["test", "important"],
            "created_at": datetime.now(UTC).isoformat()
        },
        {
            "text": "Task 3",
            "priority": 5,
            "tags": ["important"],
            "created_at": datetime.now(UTC).isoformat()
        }
    ]
    
    for task_data in tasks_data:
        response = client.post(
            f"{settings.API_V1_STR}/tasks",
            json=task_data,
            headers=auth_headers
        )
        assert response.status_code == 200
    
    # Проверяем количество созданных задач
    get_response = client.get(
        f"{settings.API_V1_STR}/tasks",
        headers=auth_headers
    )
    assert get_response.status_code == 200
    tasks = get_response.json()
    assert len(tasks) == 3

def test_delete_task(client, registered_user, auth_headers):
    """Test task deletion with various scenarios"""
    # Создаем задачу для удаления
    task_data = {
        "text": "Task to delete",
        "priority": 1,
        "tags": ["test"],
        "created_at": datetime.now(UTC).isoformat()
    }
    create_response = client.post(
        f"{settings.API_V1_STR}/tasks",
        json=task_data,
        headers=auth_headers
    )
    assert create_response.status_code == 200
    task_id = create_response.json()["id"]
    
    # Пытаемся удалить несуществующую задачу
    response = client.delete(
        f"{settings.API_V1_STR}/tasks/999",
        headers=auth_headers
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"
    
    # Пытаемся удалить задачу без авторизации
    response = client.delete(
        f"{settings.API_V1_STR}/tasks/{task_id}"
    )
    assert response.status_code == 401
    
    # Удаляем задачу
    response = client.delete(
        f"{settings.API_V1_STR}/tasks/{task_id}",
        headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Task deleted successfully"
    
    # Проверяем, что задача действительно удалена
    get_response = client.get(
        f"{settings.API_V1_STR}/tasks",
        headers=auth_headers
    )
    assert get_response.status_code == 200
    tasks = get_response.json()
    assert len(tasks) == 0

def test_delete_user(client, registered_user, auth_headers, test_notification):
    """Test user deletion"""
    # Create a task for the user
    task_data = {
        "text": "Test task",
        "priority": 1,
        "tags": ["test", "important"],
        "created_at": datetime.now(UTC).isoformat()
    }
    create_response = client.post(
        f"{settings.API_V1_STR}/tasks",
        json=task_data,
        headers=auth_headers
    )
    assert create_response.status_code == 200
    task_id = create_response.json()["id"]
    
    # Delete the user
    response = client.delete(
        f"{settings.API_V1_STR}/users/{registered_user['id']}",
        headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json() == {"message": "User deleted successfully"}
    
    # Try to login again (should fail)
    login_response = client.post(
        f"{settings.API_V1_STR}/token",
        data={
            "username": registered_user["username"],
            "password": "TestPassword123!@#"
        }
    )
    assert login_response.status_code == 401
    
    # Try to get user's tasks (should fail)
    tasks_response = client.get(
        f"{settings.API_V1_STR}/tasks",
        headers=auth_headers
    )
    assert tasks_response.status_code == 401
    
    # Try to get user's notifications (should fail)
    notifications_response = client.get(
        f"{settings.API_V1_STR}/notifications",
        headers=auth_headers
    )
    assert notifications_response.status_code == 401

def test_mark_notification_read(client, test_user_data, registered_user, auth_headers, db_session):
    """Тест отметки уведомления как прочитанного"""
    # Создаем тестовую задачу, которая создаст уведомление
    task_data = {
        "text": "Test task",
        "priority": 1,
        "due_date": "2025-01-01T00:00:00",
        "tags": ["test"]
    }
    response = client.post(
        f"{settings.API_V1_STR}/tasks",
        json=task_data,
        headers=auth_headers
    )
    assert response.status_code == 200
    
    # Дожидаемся завершения транзакции
    db_session.commit()
    
    # Получаем список уведомлений
    response = client.get(
        f"{settings.API_V1_STR}/notifications",
        headers=auth_headers
    )
    assert response.status_code == 200
    notifications = response.json()
    assert len(notifications) == 1
    
    # Отмечаем уведомление как прочитанное
    response = client.post(
        f"{settings.API_V1_STR}/notifications/{notifications[0]['id']}/read",
        headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Notification marked as read"
    
    # Проверяем, что уведомление действительно отмечено как прочитанное
    response = client.get(
        f"{settings.API_V1_STR}/notifications",
        headers=auth_headers
    )
    assert response.status_code == 200
    notifications = response.json()
    assert len(notifications) == 1
    assert notifications[0]["is_read"] is True

def test_password_reset_token(client, test_user_data, registered_user, redis_client):
    """Тест генерации и использования токена для сброса пароля"""
    # Очищаем Redis перед тестом
    redis_client.flushall()
    
    # Запрашиваем сброс пароля
    response = client.post(
        f"{settings.API_V1_STR}/password-reset",
        json={"email": test_user_data["email"]}
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Password reset email sent"
    
    # Получаем токен из Redis
    keys = redis_client.keys("reset_token:*")
    assert len(keys) == 1
    token = keys[0].split(":")[-1]
    
    # Проверяем, что токен содержит правильные данные
    token_data = redis_client.get(f"reset_token:{token}")
    assert token_data is not None
    token_data = json.loads(token_data)
    assert "user_id" in token_data
    assert token_data["user_id"] == registered_user["id"]
    
    # Сбрасываем пароль с токеном
    new_password = "NewTest123!"
    reset_response = client.post(
        f"{settings.API_V1_STR}/reset-password/{token}",
        json={"new_password": new_password}
    )
    assert reset_response.status_code == 200
    assert reset_response.json()["message"] == "Password reset successful"
    
    # Проверяем, что токен удален из Redis
    assert redis_client.get(f"reset_token:{token}") is None
    
    # Пробуем войти с новым паролем
    login_response = client.post(
        f"{settings.API_V1_STR}/token",
        data={
            "username": test_user_data["username"],
            "password": new_password
        }
    )
    assert login_response.status_code == 200
    assert "access_token" in login_response.json()

def test_password_reset_expired_token(client, test_user_data, registered_user, redis_client):
    """Тест сброса пароля с истекшим токеном"""
    # Очищаем Redis перед тестом
    redis_client.flushall()
    
    # Запрашиваем сброс пароля
    response = client.post(
        f"{settings.API_V1_STR}/password-reset",
        json={"email": test_user_data["email"]}
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Password reset email sent"
    
    # Получаем токен из Redis
    keys = redis_client.keys("reset_token:*")
    assert len(keys) == 1
    token = keys[0].split(":")[-1]
    
    # Проверяем, что токен содержит правильные данные
    token_data = redis_client.get(f"reset_token:{token}")
    assert token_data is not None
    token_data = json.loads(token_data)
    assert "user_id" in token_data
    assert token_data["user_id"] == registered_user["id"]
    
    # Удаляем токен из Redis, имитируя истечение срока действия
    redis_client.delete(f"reset_token:{token}")
    
    # Пробуем сбросить пароль с истекшим токеном
    reset_response = client.post(
        f"{settings.API_V1_STR}/reset-password/{token}",
        json={"new_password": "NewTest123!"}
    )
    assert reset_response.status_code == 400
    assert reset_response.json()["detail"] == "Invalid or expired token"
    
    # Проверяем, что старый пароль все еще работает
    old_login_response = client.post(
        f"{settings.API_V1_STR}/token",
        data={
            "username": test_user_data["username"],
            "password": test_user_data["password"]
        }
    )
    assert old_login_response.status_code == 200
    assert "access_token" in old_login_response.json()

# Redis-specific tests
def test_redis_set_get(redis_client):
    """Test basic Redis set and get operations"""
    key = "test_key"
    value = "test_value"
    redis_client.set(key, value)
    assert redis_client.get(key) == value

def test_redis_setex(redis_client):
    """Test Redis setex operation with expiration"""
    key = "test_key"
    value = "test_value"
    ttl = 1
    redis_client.setex(key, ttl, value)
    assert redis_client.get(key) == value
    time.sleep(ttl + 0.1)
    assert redis_client.get(key) is None

def test_redis_expire(redis_client):
    """Test Redis expire operation"""
    key = "test_key"
    value = "test_value"
    ttl = 1
    redis_client.set(key, value)
    assert redis_client.expire(key, ttl) is True
    assert redis_client.get(key) == value
    time.sleep(ttl + 0.1)
    assert redis_client.get(key) is None

def test_redis_ttl(redis_client):
    """Test Redis ttl operation"""
    key = "test_key"
    value = "test_value"
    ttl = 2
    redis_client.setex(key, ttl, value)
    remaining_ttl = redis_client.ttl(key)
    assert 0 < remaining_ttl <= ttl
    time.sleep(1)
    assert 0 < redis_client.ttl(key) < remaining_ttl

def test_redis_keys(redis_client):
    """Test Redis keys operation"""
    redis_client.set("key1", "value1")
    redis_client.set("key2", "value2")
    keys = redis_client.keys("*")
    assert len(keys) == 2
    assert "key1" in keys
    assert "key2" in keys

def test_redis_delete(redis_client):
    """Test Redis delete operation"""
    key = "test_key"
    value = "test_value"
    redis_client.set(key, value)
    assert redis_client.get(key) == value
    redis_client.delete(key)
    assert redis_client.get(key) is None

def test_redis_flushall(redis_client):
    """Test Redis flushall operation"""
    redis_client.set("key1", "value1")
    redis_client.set("key2", "value2")
    redis_client.flushall()
    assert len(redis_client.keys("*")) == 0

def test_notifications_caching(client, test_user_data, registered_user, auth_headers, redis_client, db_session):
    """Тест кэширования уведомлений"""
    # Создаем тестовую задачу, которая создаст уведомление
    task_data = {
        "text": "Test task",
        "priority": 1,
        "due_date": "2025-01-01T00:00:00",
        "tags": ["test"]
    }
    response = client.post(
        f"{settings.API_V1_STR}/tasks",
        json=task_data,
        headers=auth_headers
    )
    assert response.status_code == 200
    
    # Дожидаемся завершения транзакции
    db_session.commit()
    
    # Первый запрос - данные берутся из БД и кэшируются
    response = client.get(
        f"{settings.API_V1_STR}/notifications",
        headers=auth_headers
    )
    assert response.status_code == 200
    notifications = response.json()
    assert len(notifications) == 1
    
    # Проверяем, что данные закэшировались
    cache_key = f"user_notifications:{registered_user['id']}"
    cached_data = redis_client.get(cache_key)
    assert cached_data is not None
    
    # Проверяем TTL кэша
    ttl = redis_client.ttl(cache_key)
    assert ttl > 0
    assert ttl <= settings.CACHE_TTL

def test_notifications_cache_expiration(client, test_user_data, registered_user, auth_headers, redis_client, db_session):
    """Тест истечения срока действия кэша уведомлений"""
    # Создаем тестовую задачу, которая создаст уведомление
    task_data = {
        "text": "Test task",
        "priority": 1,
        "due_date": "2025-01-01T00:00:00",
        "tags": ["test"]
    }
    response = client.post(
        f"{settings.API_V1_STR}/tasks",
        json=task_data,
        headers=auth_headers
    )
    assert response.status_code == 200
    
    # Дожидаемся завершения транзакции
    db_session.commit()
    
    # Первый запрос - данные берутся из БД и кэшируются
    response = client.get(
        f"{settings.API_V1_STR}/notifications",
        headers=auth_headers
    )
    assert response.status_code == 200
    notifications = response.json()
    assert len(notifications) == 1
    
    # Проверяем TTL кэша
    cache_key = f"user_notifications:{registered_user['id']}"
    ttl = redis_client.ttl(cache_key)
    assert ttl > 0
    assert ttl <= settings.CACHE_TTL
    
    # Удаляем кэш
    redis_client.delete(cache_key)
    
    # Проверяем, что кэш удален
    assert redis_client.get(cache_key) is None 