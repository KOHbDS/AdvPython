"""
# URL Shortener API

Сервис сокращения URL-адресов с аутентификацией и аналитикой переходов.

## Описание API

URL Shortener API предоставляет следующие возможности:
- Создание сокращенных URL
- Получение статистики по переходам
- Управление пользователями
- Аутентификация и авторизация

### Основные эндпоинты

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/` | Главная страница с информацией о сервисе |
| GET | `/docs` | Swagger UI документация |
| POST | `/links/shorten` | Создание короткой ссылки |
| GET | `/{short_code}` | Перенаправление по короткой ссылке |
| GET | `/links/{short_code}` | Получение информации о ссылке |
| PUT | `/links/{short_code}` | Обновление ссылки |
| DELETE | `/links/{short_code}` | Удаление ссылки |
| GET | `/links/{short_code}/stats` | Получение статистики по ссылке |
| POST | `/users/` | Регистрация нового пользователя |
| POST | `/token` | Получение JWT токена |
| GET | `/links/search` | Поиск ссылки по оригинальному URL |
| GET | `/expired-links` | Получение списка истекших ссылок |
| POST | `/links/cleanup` | Очистка неиспользуемых ссылок |
| GET | `/healthz` | Проверка работоспособности сервиса |

## Примеры запросов

### Регистрация пользователя

```bash
curl -X 'POST' \
  'http://localhost:8000/users/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "username": "test_user",
  "email": "user@example.com",
  "password": "password123"
}'
```
### Получение токена
```bash
curl -X 'POST' \
  'http://localhost:8000/token' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=test_user&password=password123'
```

### Создание короткой ссылки
```bash
curl -X 'POST' \
  'http://localhost:8000/links/shorten' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer YOUR_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
  "original_url": "https://example.com/very/long/url/that/needs/shortening",
  "custom_alias": "my-link"
}'
```

### Создание ссылки с датой истечения срока
```bash
curl -X 'POST' \
  'http://localhost:8000/links/shorten' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer YOUR_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
  "original_url": "https://example.com/expiring-content",
  "custom_alias": "expires-soon",
  "expires_at": "2025-04-30T00:00:00"
}'
```

### Получение статистики по ссылке
```bash
curl -X 'GET' \
  'http://localhost:8000/links/my-link/stats' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer YOUR_TOKEN'
```

### Поиск ссылки по оригинальному URL
```bash
curl -X 'GET' \
  'http://localhost:8000/links/search?original_url=https://example.com/very/long/url/that/needs/shortening' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer YOUR_TOKEN'
```

### Обновление ссылки

```bash
curl -X 'PUT' \
  'http://localhost:8000/links/my-link' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer YOUR_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
  "original_url": "https://new-example.com/updated-url"
}'
```
### Удаление ссылки
```bash
curl -X 'DELETE' \
  'http://localhost:8000/links/my-link' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer YOUR_TOKEN'
```

## Инструкция по запуску

### Предварительные требования
- Docker и Docker Compose
- Git

## Запуск с Docker Compose

Клонируйте репозиторий:
```bash
git clone https://github.com/yourusername/url-shortener.git
cd url-shortener
```

Создайте файл .env с необходимыми переменными окружения или используйте значения по умолчанию:
```text
# Database settings
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
POSTGRES_DB=url_shortener
POSTGRES_HOST=db
POSTGRES_PORT=5432

# Redis settings
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

# Security settings
SECRET_KEY=your_secret_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Environment settings
ENVIRONMENT=production
LOG_LEVEL=INFO
```

Запустите контейнеры с помощью Docker Compose:
```bash
docker-compose up -d
```

Приложение будет доступно по адресу http://localhost:8000. Документация API доступна по адресу http://localhost:8000/docs.
```bash
docker-compose exec web pytest
```

Для запуска тестов с отчетом о покрытии:
```bash
docker-compose exec web pytest --cov=app tests/
```

## Описание базы данных

### Основные таблицы

#### users
- id: Уникальный идентификатор пользователя (PRIMARY KEY)
- username: Уникальное имя пользователя
- email: Email пользователя
- hashed_password: Хэшированный пароль
- is_active: Статус активности аккаунта
- created_at: Время создания аккаунта

#### links
- id: Уникальный идентификатор ссылки (PRIMARY KEY)
- short_code: Короткий идентификатор для URL (уникальный)
- original_url: Оригинальный URL
- custom_alias: Пользовательский алиас (опционально)
- clicks: Количество переходов
- created_at: Время создания ссылки
- last_used: Время последнего использования
- expires_at: Время истечения срока действия (опционально)
- is_active: Статус активности ссылки
- owner_id: ID пользователя, создавшего ссылку (FOREIGN KEY)

#### expired_links
- id: Уникальный идентификатор (PRIMARY KEY)
- short_code: Короткий идентификатор
- original_url: Оригинальный URL
- created_at: Время создания ссылки
- expired_at: Время истечения срока действия
- total_clicks: Общее количество переходов
- owner_id: ID пользователя (FOREIGN KEY)

## Технологии

- Backend: FastAPI, Python 3.9+
- База данных: PostgreSQL
- Кэширование: Redis
- Аутентификация: JWT токены
- Документация: Swagger UI
- Контейнеризация: Docker, Docker Compose