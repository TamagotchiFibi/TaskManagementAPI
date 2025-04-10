import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from pathlib import Path
import os
from dotenv import load_dotenv
from sqlalchemy.sql import delete
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.main import app
from app.db.database import Base, get_db
from app.models import User, Notification, Task, Tag
from app.core.security import get_password_hash
from app.utils.cache import get_redis_client, MockRedis
from app.core.config import settings

# Load test environment
env_path = Path(__file__).parent.parent.parent / ".env.test"
load_dotenv(env_path)

# Set TESTING flag
os.environ["TESTING"] = "True"

@pytest.fixture(scope="session")
def engine():
    """Create a SQLite in-memory database engine for the test session"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    return engine

@pytest.fixture
def db_session(engine):
    """Create a fresh database session for each test"""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    
    # Очищаем базу данных перед каждым тестом
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(autouse=True)
def clear_redis(redis_client):
    """Очищает Redis перед каждым тестом"""
    redis_client.flushall()
    yield
    redis_client.flushall()

@pytest.fixture
def redis_client():
    """Создает новый экземпляр MockRedis для каждого теста"""
    from app.utils.cache import mock_redis
    mock_redis.flushall()
    return mock_redis

@pytest.fixture
def client(redis_client):
    """Создает тестовый клиент с изолированным Redis"""
    def override_get_redis():
        return redis_client
    
    app.dependency_overrides[get_redis_client] = override_get_redis
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def test_user_data():
    """Test user data fixture"""
    return {
        "username": "testuser123",
        "email": "test@example.com",
        "password": "TestPassword123!@#"
    }

@pytest.fixture
def test_user(db_session, test_user_data):
    """Create a test user directly in the database"""
    user = User(
        username=test_user_data["username"],
        email=test_user_data["email"],
        hashed_password=get_password_hash(test_user_data["password"]),
        is_active=True,
        email_verified=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def auth_headers(test_user, client):
    """Get authentication headers for test user"""
    response = client.post(
        f"{settings.API_V1_STR}/token",
        data={
            "username": test_user.username,
            "password": "TestPassword123!@#"
        }
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def test_notification(db_session, test_user):
    """Create a test notification"""
    notification = Notification(
        user_id=test_user.id,
        title="Test Notification",
        message="Test notification message",
        read=False
    )
    db_session.add(notification)
    db_session.commit()
    db_session.refresh(notification)
    return notification

@pytest.fixture
async def async_session() -> AsyncSession:
    """Create async session for tests"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with async_session() as session:
        yield session
        await session.rollback()
        await session.close()
    
    await engine.dispose() 