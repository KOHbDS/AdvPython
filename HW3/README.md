URL Shortener APIСервис сокращения URL-адресов с аутентификацией и аналитикой переходов.Описание APIURL Shortener API предоставляет следующие возможности:

Создание сокращенных URL
Получение статистики по переходам
Управление пользователями
Аутентификация и авторизация
Основные эндпоинтыМетодПутьОписаниеGET/Главная страница с информацией о сервисеGET/docsSwagger UI документацияPOST/api/shortenСоздание сокращенного URLGET/{short_id}Перенаправление по сокращенному URLGET/api/linksПолучение всех ссылок пользователяGET/api/links/{short_id}Получение информации о конкретной ссылкеGET/api/links/{short_id}/statsПолучение статистики по ссылкеPOST/api/auth/registerРегистрация нового пользователяPOST/api/auth/tokenПолучение JWT токенаGET/api/users/meПолучение информации о текущем пользователеПримеры запросовРегистрация пользователяbashcurl -X 'POST' \
'https://url-shortener-uaim.onrender.com/api/auth/register' \
-H 'accept: application/json' \
-H 'Content-Type: application/json' \
-d '{
"username": "test_user",
"email": "mailto:user@example.com",
"password": "secure_password"
}'
Получение токена
bashcurl -X 'POST' \
'https://url-shortener-uaim.onrender.com/api/auth/token' \
-H 'accept: application/json' \
-H 'Content-Type: application/x-www-form-urlencoded' \
-d 'username=test_user&password=secure_password'
Создание сокращенного URL (авторизованный пользователь)
bashcurl -X 'POST' \
'https://url-shortener-uaim.onrender.com/api/shorten' \
-H 'accept: application/json' \
-H 'Authorization: Bearer YOUR_TOKEN_HERE' \
-H 'Content-Type: application/json' \
-d '{
"original_url": "https://example.com/very/long/url/that/needs/shortening",
"custom_id": "my-custom-id"  # опционально
}'
Создание сокращенного URL (анонимный пользователь)
bashcurl -X 'POST' \
'https://url-shortener-uaim.onrender.com/api/shorten' \
-H 'accept: application/json' \
-H 'Content-Type: application/json' \
-d '{
"original_url": "https://example.com/very/long/url/that/needs/shortening"
}'
Получение статистики по ссылке
bashcurl -X 'GET' \
'https://url-shortener-uaim.onrender.com/api/links/my-custom-id/stats' \
-H 'accept: application/json' \
-H 'Authorization: Bearer YOUR_TOKEN_HERE'

Описание базы данных
Основные таблицы
users

id: Уникальный идентификатор пользователя (PRIMARY KEY)
username: Уникальное имя пользователя
email: Email пользователя
hashed_password: Хэшированный пароль
is_active: Статус активности аккаунта
created_at: Время создания аккаунта

links

id: Уникальный идентификатор ссылки (PRIMARY KEY)
short_id: Короткий идентификатор для URL (уникальный)
original_url: Оригинальный URL
user_id: ID пользователя, создавшего ссылку (FOREIGN KEY)
created_at: Время создания ссылки
is_active: Статус активности ссылки

clicks

id: Уникальный идентификатор клика (PRIMARY KEY)
link_id: ID ссылки (FOREIGN KEY)
clicked_at: Время клика
user_agent: User-Agent браузера
ip_address: IP-адрес пользователя
referrer: Реферер (откуда пришел пользователь)

Технологии

Backend: FastAPI, Python 3.9+
База данных: PostgreSQL
Кэширование: Redis
Аутентификация: JWT токены
Документация: Swagger UI, ReDoc
Размещение: Render.com