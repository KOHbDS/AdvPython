import os
from typing import Optional

# Базовые настройки
SECRET_KEY = os.getenv("SECRET_KEY", "YOUR_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# Настройки базы данных
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
POSTGRES_DB = os.getenv("POSTGRES_DB", "url_shortener")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

# Настройки Redis
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

# Флаг для определения режима тестирования
TESTING = os.getenv("TESTING", "False").lower() in ("true", "1", "t")

# URL для подключения к базе данных
# Render предоставляет DATABASE_URL для PostgreSQL
DATABASE_URL_FROM_ENV: Optional[str] = os.getenv("DATABASE_URL")

if TESTING:
    DATABASE_URL = "sqlite:///./test.db"
elif DATABASE_URL_FROM_ENV:
    # Используем URL, предоставленный Render
    DATABASE_URL = DATABASE_URL_FROM_ENV
else:
    DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
