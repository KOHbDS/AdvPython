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
| POST | `/api/shorten` | Создание сокращенного URL |
| GET | `/{short_id}` | Перенаправление по сокращенному URL |
| GET | `/api/links` | Получение всех ссылок пользователя |
| GET | `/api/links/{short_id}` | Получение информации о конкретной ссылке |
| GET | `/api/links/{short_id}/stats` | Получение статистики по ссылке |
| POST | `/api/auth/register` | Регистрация нового пользователя |
| POST | `/api/auth/token` | Получение JWT токена |
| GET | `/api/users/me` | Получение информации о текущем пользователе |

## Примеры запросов

### Регистрация пользователя

```bash
curl -X 'POST' \
  'https://url-shortener-uaim.onrender.com/api/auth/register' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "username": "test_user",
  "email": "user@example.com",
  "password": "secure_password"
}'
```

# Описание базы данных
## Основные таблицы
### users

- id: Уникальный идентификатор пользователя (PRIMARY KEY)
- username: Уникальное имя пользователя
- email: Email пользователя
- hashed_password: Хэшированный пароль
- is_active: Статус активности аккаунта
- created_at: Время создания аккаунта

### links

- id: Уникальный идентификатор ссылки (PRIMARY KEY)
- short_id: Короткий идентификатор для URL (уникальный)
- original_url: Оригинальный URL
- user_id: ID пользователя, создавшего ссылку (FOREIGN KEY)
- created_at: Время создания ссылки
- is_active: Статус активности ссылки

### clicks

- id: Уникальный идентификатор клика (PRIMARY KEY)
- link_id: ID ссылки (FOREIGN KEY)
- clicked_at: Время клика
- user_agent: User-Agent браузера
- ip_address: IP-адрес пользователя
- referrer: Реферер (откуда пришел пользователь)

# Технологии

- Backend: FastAPI, Python 3.9+
- База данных: PostgreSQL
- Кэширование: Redis
- Аутентификация: JWT токены
- Документация: Swagger UI, ReDoc
- Размещение: Render.com
