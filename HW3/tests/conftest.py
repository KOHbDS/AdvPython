import pytest
import os
import sys
from typing import Generator, Any
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine
from fastapi.testclient import TestClient
import pytest
import asyncio
from pytest_asyncio import fixture as asyncio_fixture

os.environ["TESTING"] = "True"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import Base, get_db
from app.main import app
from app import models, auth

TEST_DATABASE_URL = "sqlite:///:memory:"

engine: Engine = create_engine(
    TEST_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """
    Создает тестовую базу данных и возвращает сессию
    """
    Base.metadata.create_all(bind=engine)

    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()

    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(db: Session) -> Generator[TestClient, None, None]:
    """
    Создает тестовый клиент с переопределенной зависимостью базы данных
    """
    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    test_client = TestClient(app)
    
    yield test_client

    app.dependency_overrides.clear()

@pytest.fixture
def test_user(db: Session) -> models.User:
    """
    Создает тестового пользователя
    """
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "password123"
    }
    
    db_user = db.query(models.User).filter(models.User.username == user_data["username"]).first()
    if db_user:
        return db_user
    
    hashed_password = auth.get_password_hash(user_data["password"])
    db_user = models.User(
        username=user_data["username"],
        email=user_data["email"],
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user

@pytest.fixture
def auth_token(client: TestClient, test_user: models.User) -> str:
    """
    Получает токен аутентификации для тестового пользователя
    """
    response = client.post(
        "/token",
        data={"username": test_user.username, "password": "password123"}
    )
    return response.json()["access_token"]

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()