import pytest
from app import models

def test_create_user(client, db):
    # Тестируем создание пользователя
    response = client.post(
        "/users/",
        json={"username": "testuser", "email": "test@example.com", "password": "password123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    assert "id" in data
    assert "created_at" in data

def test_duplicate_username(client, db):
    # Создаем первого пользователя
    client.post(
        "/users/",
        json={"username": "testuser", "email": "test@example.com", "password": "password123"}
    )
    
    # Пытаемся создать пользователя с тем же именем
    response = client.post(
        "/users/",
        json={"username": "testuser", "email": "another@example.com", "password": "password123"}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Username already registered"

def test_login(client, db):
    # Создаем пользователя
    client.post(
        "/users/",
        json={"username": "testuser", "email": "test@example.com", "password": "password123"}
    )
    
    # Логинимся
    response = client.post(
        "/token",
        data={"username": "testuser", "password": "password123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_wrong_password(client, db):
    # Создаем пользователя
    client.post(
        "/users/",
        json={"username": "testuser", "email": "test@example.com", "password": "password123"}
    )
    
    # Пытаемся залогиниться с неправильным паролем
    response = client.post(
        "/token",
        data={"username": "testuser", "password": "wrongpassword"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"
