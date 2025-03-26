# tests/test_database.py
import pytest
from sqlalchemy.orm import Session
from app.database import get_db, Base, engine

def test_get_db():
    """Тест функции получения сессии БД"""
    db_gen = get_db()
    
    db = next(db_gen)
    assert isinstance(db, Session)
    
    try:
        next(db_gen)
    except StopIteration:
        pass
    assert db is not None

def test_base_metadata():
    """Тест метаданных базы данных"""
    tables = Base.metadata.tables
    assert "users" in tables
    assert "links" in tables
    assert "expired_links" in tables

    users_table = tables["users"]
    assert "id" in users_table.columns
    assert "username" in users_table.columns
    assert "email" in users_table.columns
    assert "hashed_password" in users_table.columns
