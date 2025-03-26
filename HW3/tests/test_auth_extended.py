# tests/test_auth_extended.py
import pytest
from datetime import datetime, timedelta
from fastapi import HTTPException
from jose import jwt
import asyncio
from app import auth, models, schemas
from app.config import SECRET_KEY, ALGORITHM

def test_password_hashing():
    """Тест хеширования и проверки пароля"""
    password = "test_password"
    hashed = auth.get_password_hash(password)
    
    assert hashed != password
    
    assert auth.verify_password(password, hashed) is True
    
    assert auth.verify_password("wrong_password", hashed) is False

def test_jwt_token_creation_and_decoding():
    """Тест создания и декодирования JWT токена"""
    test_data = {"sub": "testuser"}
    token = auth.create_access_token(test_data)
    
    assert token is not None
    assert len(token) > 0
    
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    
    assert payload["sub"] == "testuser"
    assert "exp" in payload

@pytest.mark.asyncio
async def test_get_current_user_with_invalid_token(db):
    """Тест получения пользователя с невалидным токеном"""
    invalid_token = "invalid.token.string"
    
    with pytest.raises(HTTPException) as exc_info:
        await auth.get_current_user(invalid_token, db)
    
    assert exc_info.value.status_code == 401
    assert "Could not validate credentials" in exc_info.value.detail

@pytest.mark.asyncio
async def test_get_current_user_with_nonexistent_user(db):
    """Тест получения несуществующего пользователя"""
    token = auth.create_access_token({"sub": "nonexistent_user"})
    
    with pytest.raises(HTTPException) as exc_info:
        await auth.get_current_user(token, db)
    
    assert exc_info.value.status_code == 401

@pytest.mark.asyncio
async def test_get_current_active_user_with_inactive_user():
    """Тест получения неактивного пользователя"""
    inactive_user = models.User(
        username="inactive",
        email="inactive@example.com",
        hashed_password=auth.get_password_hash("password"),
        is_active=False
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await auth.get_current_active_user(inactive_user)
    
    assert exc_info.value.status_code == 400
    assert "Inactive user" in exc_info.value.detail

@pytest.mark.asyncio
async def test_get_optional_user_with_valid_token(db, test_user):
    """Тест получения опционального пользователя с валидным токеном"""
    token = auth.create_access_token({"sub": test_user.username})
    
    user = await auth.get_optional_user(token, db)
    
    assert user is not None
    assert user.username == test_user.username

@pytest.mark.asyncio
async def test_get_optional_user_with_invalid_token(db):
    """Тест получения опционального пользователя с невалидным токеном"""
    user = await auth.get_optional_user("invalid.token", db)
    
    assert user is None
    
    user = await auth.get_optional_user(None, db)
    assert user is None
