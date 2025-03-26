import pytest
import os
import sys
from typing import Generator, Any
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine
from fastapi.testclient import TestClient

# Устанавливаем флаг тестирования
os.environ["TESTING"] = "True"

# Добавляем корневую директорию проекта в sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import Base, get_db
from app.main import app
from app import models, auth

# Настройка тестовой базы данных
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
    # Создаем таблицы
    Base.metadata.create_all(bind=engine)

    # Создаем транзакцию
    connection = engine.connect()
    transaction = connection.begin()

    # Создаем сессию
    session = TestingSessionLocal(bind=connection)

    yield session

    # Закрываем сессию и откатываем транзакцию
    session.close()
    transaction.rollback()
    connection.close()

    # Удаляем таблицы
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
    
    # Переопределяем зависимость get_db
    app.dependency_overrides[get_db] = override_get_db
    
    # Создаем тестовый клиент
    test_client = TestClient(app)
    
    yield test_client

    # Очищаем переопределения зависимостей
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
    
    # Проверяем, существует ли пользователь
    db_user = db.query(models.User).filter(models.User.username == user_data["username"]).first()
    if db_user:
        return db_user
    
    # Создаем пользователя
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
