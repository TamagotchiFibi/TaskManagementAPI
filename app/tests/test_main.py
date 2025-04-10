# Copyright (c) 2024 Task Management API
# Licensed under the MIT License

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.db.database import Base, get_db
from app.models import User, UserRole
from app.utils import get_password_hash
from config import settings

# Настройка тестовой базы данных
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Создание таблиц
Base.metadata.create_all(bind=engine)

def override_get_db():
    """Переопределение функции получения сессии для тестов"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# Подмена зависимости для тестов
app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture(autouse=True)
def clear_database():
    """Очистка базы данных перед каждым тестом"""
    db = TestingSessionLocal()
    try:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        yield
    finally:
        db.close()

def test_register_user():
    """Тест регистрации нового пользователя"""
    response = client.post(f"{settings.API_V1_STR}/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "TestPass123!"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    assert data["role"] == "user"
    assert "id" in data

def test_register_duplicate_user():
    """Тест регистрации существующего пользователя"""
    client.post(f"{settings.API_V1_STR}/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "TestPass123!"
    })
    response = client.post(f"{settings.API_V1_STR}/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "TestPass123!"
    })
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]

def test_register_weak_password():
    """Тест валидации слабого пароля"""
    response = client.post(f"{settings.API_V1_STR}/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "weak"
    })
    assert response.status_code == 422
    assert "password" in response.json()["detail"][0]["loc"]

def test_login_success():
    """Тест успешного входа"""
    client.post(f"{settings.API_V1_STR}/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "TestPass123!"
    })
    response = client.post(f"{settings.API_V1_STR}/token", data={
        "username": "testuser",
        "password": "TestPass123!"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

def test_login_failure():
    """Тест неудачного входа"""
    response = client.post(f"{settings.API_V1_STR}/token", data={
        "username": "wronguser",
        "password": "wrongpass"
    })
    assert response.status_code == 401
    assert "Incorrect username or password" in response.json()["detail"]

def test_create_task():
    """Тест создания задачи"""
    # Регистрация и вход
    client.post(f"{settings.API_V1_STR}/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "TestPass123!"
    })
    login_response = client.post(f"{settings.API_V1_STR}/token", data={
        "username": "testuser",
        "password": "TestPass123!"
    })
    token = login_response.json()["access_token"]
    
    # Создание задачи
    response = client.post(
        f"{settings.API_V1_STR}/tasks",
        json={
            "text": "Test task",
            "priority": 3,
            "tags": ["work", "urgent"]
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["text"] == "Test task"
    assert data["priority"] == 3
    assert set(data["tags"]) == {"work", "urgent"}

def test_get_tasks():
    """Тест получения списка задач"""
    # Регистрация и вход
    client.post(f"{settings.API_V1_STR}/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "TestPass123!"
    })
    login_response = client.post(f"{settings.API_V1_STR}/token", data={
        "username": "testuser",
        "password": "TestPass123!"
    })
    token = login_response.json()["access_token"]
    
    # Создание задач
    client.post(
        f"{settings.API_V1_STR}/tasks",
        json={
            "text": "Task 1",
            "priority": 3,
            "tags": ["work"]
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    client.post(
        f"{settings.API_V1_STR}/tasks",
        json={
            "text": "Task 2",
            "priority": 1,
            "tags": ["personal"]
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Получение задач
    response = client.get(
        f"{settings.API_V1_STR}/tasks",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) == 2
    assert tasks[0]["text"] == "Task 1"
    assert tasks[0]["tags"] == ["work"]
    assert tasks[1]["text"] == "Task 2"
    assert tasks[1]["tags"] == ["personal"]

def test_delete_task_admin():
    """Тест удаления задачи администратором"""
    # Создание администратора
    db = TestingSessionLocal()
    admin = User(
        username="admin",
        email="admin@example.com",
        hashed_password=get_password_hash("AdminPass123!"),
        role=UserRole.ADMIN
    )
    db.add(admin)
    db.commit()
    db.close()
    
    # Вход администратора
    login_response = client.post(f"{settings.API_V1_STR}/token", data={
        "username": "admin",
        "password": "AdminPass123!"
    })
    admin_token = login_response.json()["access_token"]
    
    # Создание задачи обычным пользователем
    client.post(f"{settings.API_V1_STR}/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "TestPass123!"
    })
    user_login = client.post(f"{settings.API_V1_STR}/token", data={
        "username": "testuser",
        "password": "TestPass123!"
    })
    user_token = user_login.json()["access_token"]
    
    task_response = client.post(
        f"{settings.API_V1_STR}/tasks",
        json={
            "text": "Test task",
            "priority": 3
        },
        headers={"Authorization": f"Bearer {user_token}"}
    )
    task_id = task_response.json()["id"]
    
    # Удаление задачи администратором
    response = client.delete(
        f"{settings.API_V1_STR}/tasks/{task_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Task deleted successfully"

def test_password_reset():
    """Тест сброса пароля"""
    # Регистрация пользователя
    client.post(f"{settings.API_V1_STR}/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "TestPass123!"
    })
    
    # Запрос на сброс пароля
    response = client.post(
        f"{settings.API_V1_STR}/password-reset",
        json={"email": "test@example.com"}
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Password reset email sent"
    
    # TODO: Добавить тест для проверки токена сброса пароля
    # Это потребует мокирования Redis и email-сервиса 