import pytest
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# Устанавливаем флаг тестирования
os.environ["TESTING"] = "True"

# Добавляем корневой каталог проекта в sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Импортируем после установки переменной окружения
from app.database import Base, get_db
from app.main import app

# Настройка тестовой базы данных
TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db():
    # Создаем таблицы перед каждым тестом
    Base.metadata.create_all(bind=engine)
    
    # Создаем соединение с базой данных
    connection = engine.connect()
    transaction = connection.begin()
    
    # Создаем сессию привязанную к транзакции
    session = TestingSessionLocal(bind=connection)
    
    # Возвращаем сессию для использования в тестах
    yield session
    
    # Закрываем сессию и откатываем транзакцию
    session.close()
    transaction.rollback()
    connection.close()
    
    # Удаляем таблицы после теста
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(db):
    # Переопределяем зависимость для получения тестовой БД
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    # Используем TestClient для отправки запросов
    test_client = TestClient(app)
    
    yield test_client
    
    # Очищаем переопределения после теста
    app.dependency_overrides.clear()
