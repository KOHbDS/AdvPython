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
| GET | `/docs-v2` | Swagger UI документация |
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

Приложение будет доступно по адресу http://localhost:8000. Документация API доступна по адресу http://localhost:8000/docs-v2.
```bash
docker-compose exec web pytest
```

Для запуска тестов с отчетом о покрытии:
```bash
./generate_coverage.sh
```
отчет в **HW3/htmlcov/index.html**

Для запуска нагрузочного тестирование используйте 
```bash
locust -f tests/locustfile.py --host=http://localhost:8000 --headless -u 10 -r 1 -t 30s
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

# Отчет о тестировании URL Shortener API

## 1. Общие результаты тестирования

### Покрытие кода

Тестирование показало высокий уровень покрытия кода (91%), что указывает на хорошую проработку тестов. Детальное покрытие по модулям:

| Модуль | Покрытие |
|--------|----------|
| app/models.py | 100% |
| app/schemas.py | 100% |
| app/background_tasks.py | 100% |
| app/auth.py | 97% |
| app/config.py | 95% |
| app/database.py | 93% |
| app/cache.py | 88% |
| app/main.py | 87% |
| app/simple_docs.py | 88% |

### Результаты юнит-тестов

Все юнит-тесты успешно пройдены (116 тестов пройдено, 2 пропущено). Тесты охватывают следующие компоненты:

- Аутентификация и авторизация
- Кэширование
- Управление ссылками (создание, обновление, удаление)
- Фоновые задачи (очистка истекших и неиспользуемых ссылок)
- Перенаправление по коротким ссылкам
- Проверка здоровья системы

## 2. Результаты нагрузочного тестирования

Нагрузочное тестирование проводилось с использованием Locust с симуляцией 10 одновременных пользователей в течение 30 секунд.

### Статистика запросов

| Тип запроса | Количество запросов | Средний отклик (мс) | Мин. отклик (мс) | Макс. отклик (мс) |
|-------------|---------------------|---------------------|------------------|-------------------|
| POST /links/shorten | 27 | 12 | 8 | 49 |
| POST /users/ | 10 | 301 | 256 | 595 |
| POST /token | 10 | 272 | 262 | 293 |
| GET /{short_code} | 79 | ~7 | 4 | 34 |

### Ключевые метрики

- **Общее количество запросов**: 126
- **Запросов в секунду**: 4.29
- **Процент ошибок**: 0%
- **Средний отклик**: 53 мс

### Распределение времени отклика (перцентили)

- **50% запросов**: < 9 мс
- **75% запросов**: < 13 мс
- **90% запросов**: < 54 мс
- **95% запросов**: < 290 мс
- **100% запросов**: < 600 мс

### Анализ производительности

1. **Самые быстрые операции**: Перенаправление по коротким ссылкам (GET /{short_code}) - средний отклик около 7 мс.
2. **Самые медленные операции**: Регистрация пользователей (POST /users/) - средний отклик 301 мс.
3. **Наиболее стабильные операции**: Получение токена (POST /token) - малый разброс между минимальным и максимальным временем отклика.

