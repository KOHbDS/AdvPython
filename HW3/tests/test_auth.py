import pytest
from app import models

def test_create_user(client, db):
    """Тест создания пользователя"""
    response = client.post(
        "/users/",
        json={"username": "newuser", "email": "new@example.com", "password": "password123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "newuser"
    assert data["email"] == "new@example.com"
    assert "id" in data
    assert "created_at" in data
    
    # Проверяем, что пользователь действительно создан в базе
    db_user = db.query(models.User).filter(models.User.username == "newuser").first()
    assert db_user is not None
    assert db_user.email == "new@example.com"

def test_create_user_invalid_data(client, db):
    """Тест создания пользователя с невалидными данными"""
    # Слишком короткий пароль
    response = client.post(
        "/users/",
        json={"username": "newuser", "email": "new@example.com", "password": "short"}
    )
    assert response.status_code == 422
    
    # Невалидный email
    response = client.post(
        "/users/",
        json={"username": "newuser", "email": "invalid-email", "password": "password123"}
    )
    assert response.status_code == 422

def test_duplicate_username(client, test_user):
    """Тест создания пользователя с существующим именем"""
    response = client.post(
        "/users/",
        json={"username": test_user.username, "email": "another@example.com", "password": "password123"}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Username already registered"

def test_duplicate_email(client, test_user):
    """Тест создания пользователя с существующим email"""
    response = client.post(
        "/users/",
        json={"username": "another_user", "email": test_user.email, "password": "password123"}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"

def test_login_success(client, test_user):
    """Тест успешного входа в систему"""
    response = client.post(
        "/token",
        data={"username": test_user.username, "password": "password123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_wrong_password(client, test_user):
    """Тест входа с неправильным паролем"""
    response = client.post(
        "/token",
        data={"username": test_user.username, "password": "wrongpassword"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"

def test_login_nonexistent_user(client):
    """Тест входа с несуществующим пользователем"""
    response = client.post(
        "/token",
        data={"username": "nonexistent", "password": "password123"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"
