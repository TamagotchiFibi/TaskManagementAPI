from datetime import datetime
import pytest
from sqlalchemy.exc import IntegrityError

from app.models import User, Task
from app.schemas.user import UserCreate
from app.schemas.task import TaskCreate
from app.core.config import settings

def test_user_creation(db_session):
    """Тест создания пользователя"""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password="hashed_password"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    assert user.username == "testuser"
    assert user.email == "test@example.com"
    assert user.is_active is True
    assert isinstance(user.created_at, datetime)

def test_user_unique_constraints(client):
    """Test unique constraints for users"""
    # Create first user
    user1_data = {
        "username": "testuser1",
        "email": "test1@example.com",
        "password": "Test1234!"
    }
    response = client.post(
        f"{settings.API_V1_STR}/register",
        json=user1_data
    )
    assert response.status_code == 200

    # Try to create user with same email
    user2_data = {
        "username": "testuser2",
        "email": "test1@example.com",  # Same email as user1
        "password": "Test1234!"
    }
    response = client.post(
        f"{settings.API_V1_STR}/register",
        json=user2_data
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Username or email already registered"

    # Try to create user with same username
    user3_data = {
        "username": "testuser1",  # Same username as user1
        "email": "test3@example.com",
        "password": "Test1234!"
    }
    response = client.post(
        f"{settings.API_V1_STR}/register",
        json=user3_data
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Username or email already registered"

def test_task_creation(db_session):
    """Тест создания задачи"""
    # Создаем пользователя
    user = User(
        username="taskuser",
        email="task@example.com",
        hashed_password="hashed_password"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    # Создаем задачу
    task = Task(
        text="Test task",
        priority=3,
        owner_id=user.id
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    
    assert task.text == "Test task"
    assert task.priority == 3
    assert task.owner_id == user.id
    assert isinstance(task.created_at, datetime)

def test_task_priority_validation(db_session):
    """Тест валидации приоритета задачи"""
    # Создаем пользователя
    user = User(
        username="priorityuser",
        email="priority@example.com",
        hashed_password="hashed_password"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    # Пытаемся создать задачу с недопустимым приоритетом
    with pytest.raises(ValueError):
        Task(
            text="Invalid priority task",
            priority=6,  # Максимальный приоритет 5
            owner_id=user.id
        )
    
    with pytest.raises(ValueError):
        Task(
            text="Invalid priority task",
            priority=0,  # Минимальный приоритет 1
            owner_id=user.id
        )

def test_user_password_validation():
    """Тест валидации пароля пользователя"""
    # Валидный пароль
    user_create = UserCreate(
        username="validuser",
        email="valid@example.com",
        password="ValidPass123!"
    )
    assert user_create.password == "ValidPass123!"
    
    # Невалидные пароли
    with pytest.raises(ValueError):
        UserCreate(
            username="invaliduser",
            email="invalid@example.com",
            password="short"  # Слишком короткий
        )
    
    with pytest.raises(ValueError):
        UserCreate(
            username="invaliduser",
            email="invalid@example.com",
            password="nouppercase123!"  # Нет заглавной буквы
        )
    
    with pytest.raises(ValueError):
        UserCreate(
            username="invaliduser",
            email="invalid@example.com",
            password="NOLOWERCASE123!"  # Нет строчной буквы
        )
    
    with pytest.raises(ValueError):
        UserCreate(
            username="invaliduser",
            email="invalid@example.com",
            password="NoNumbers!"  # Нет цифр
        )
    
    with pytest.raises(ValueError):
        UserCreate(
            username="invaliduser",
            email="invalid@example.com",
            password="NoSpecial123"  # Нет специальных символов
        )

def test_task_validation():
    """Тест валидации задачи"""
    # Валидная задача
    task_create = TaskCreate(
        text="Valid task",
        priority=3
    )
    assert task_create.text == "Valid task"
    assert task_create.priority == 3
    
    # Невалидные задачи
    with pytest.raises(ValueError):
        TaskCreate(
            text="",  # Пустой текст
            priority=3
        )
    
    with pytest.raises(ValueError):
        TaskCreate(
            text="Too long task" * 100,  # Слишком длинный текст
            priority=3
        )

def test_password_validation():
    """Тест валидации пароля"""
    # Валидный пароль
    valid_user = UserCreate(
        username="testuser",
        email="test@example.com",
        password="Test1234!"
    )
    assert valid_user.password == "Test1234!"

    # Слишком короткий пароль
    with pytest.raises(ValueError) as exc_info:
        UserCreate(
            username="testuser",
            email="test@example.com",
            password="Test1!"
        )
    assert "String should have at least 8 characters" in str(exc_info.value)

    # Без заглавной буквы
    with pytest.raises(ValueError) as exc_info:
        UserCreate(
            username="testuser",
            email="test@example.com",
            password="test1234!"
        )
    assert "Password must contain at least one uppercase letter" in str(exc_info.value)

    # Без строчной буквы
    with pytest.raises(ValueError) as exc_info:
        UserCreate(
            username="testuser",
            email="test@example.com",
            password="TEST1234!"
        )
    assert "Password must contain at least one lowercase letter" in str(exc_info.value)

    # Без цифры
    with pytest.raises(ValueError) as exc_info:
        UserCreate(
            username="testuser",
            email="test@example.com",
            password="TestTest!"
        )
    assert "Password must contain at least one number" in str(exc_info.value)

    # Без специального символа
    with pytest.raises(ValueError) as exc_info:
        UserCreate(
            username="testuser",
            email="test@example.com",
            password="Test1234"
        )
    assert "Password must contain at least one special character" in str(exc_info.value) 