import logging
import os
import shortuuid
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any

from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks, Request
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from sqlalchemy.orm import Session
from sqlalchemy import text

from . import models, schemas, database, auth, cache, background_tasks as bg_tasks
from .database import engine, get_db
from .simple_docs import add_custom_docs

# Настройка логирования
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        # Удаляем FileHandler и оставляем только StreamHandler
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# Логируем запуск приложения
logger.info("Starting URL Shortener API")

# Создаем таблицы в базе данных
models.Base.metadata.create_all(bind=engine)

# Настройки CORS
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

app = FastAPI(
    title="URL Shortener API",
    description="API for shortening URLs with statistics and user management",
    version="1.0.0"
)

# Добавляем CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# # Добавляем пользовательскую документацию
# add_custom_docs(app)


@app.get("/")
async def root() -> Dict[str, str]:
    """
    Root endpoint for URL Shortener API
    """
    return {"message": "Welcome to URL Shortener API. Go to /docs for documentation."}


# Middleware для обработки исключений
@app.middleware("http")
async def log_exceptions(request: Request, call_next) -> JSONResponse:
    try:
        return await call_next(request)
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Не раскрываем детали ошибки в production
        error_detail = str(e) if os.getenv("ENVIRONMENT") == "development" else "Internal Server Error"
        
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error", "error": error_detail}
        )

# Обработчики событий
@app.on_event("startup")
async def startup_event() -> None:
    """
    Выполняется при запуске приложения
    """
    logger.info("Application startup")
    
    # Проверка подключения к базе данных
    try:
        db = next(get_db())
        try:
            result = db.execute(text("SELECT 1")).fetchone()
            logger.info(f"Database connection successful: {result}")
        except Exception as e:
            logger.error(f"Database connection failed: {str(e)}")
            logger.error(traceback.format_exc())
    except Exception as e:
        logger.error(f"Error getting database session: {str(e)}")
        logger.error(traceback.format_exc())
    
    # Проверка подключения к Redis
    try:
        if cache.redis_client:
            redis_result = cache.redis_client.ping()
            logger.info(f"Redis connection successful: {redis_result}")
        else:
            logger.warning("Redis client is not initialized. Cache functionality will be limited.")
    except Exception as e:
        logger.error(f"Redis connection failed: {str(e)}")
        logger.warning("Application will continue without Redis caching")



# Endpoint для регистрации пользователя
@app.post("/users/", response_model=schemas.UserResponse)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)) -> models.User:
    """
    Регистрация нового пользователя
    """
    logger.debug(f"Attempting to create user with username: {user.username}")
    
    # Проверка существования пользователя с таким именем
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        logger.warning(f"Username already registered: {user.username}")
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # Проверка существования пользователя с таким email
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        logger.warning(f"Email already registered: {user.email}")
        raise HTTPException(status_code=400, detail="Email already registered")
    
    try:
        # Хеширование пароля и создание пользователя
        hashed_password = auth.get_password_hash(user.password)
        db_user = models.User(username=user.username, email=user.email, hashed_password=hashed_password)
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        logger.info(f"User created successfully: {user.username}")
        return db_user
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating user: {str(e)}")
        raise HTTPException(status_code=500, detail="Error creating user")

# Endpoint для получения токена доступа
@app.post("/token", response_model=schemas.Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Получение JWT токена для аутентификации
    """
    logger.debug(f"Login attempt for username: {form_data.username}")
    
    # Аутентификация пользователя
    user = auth.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        logger.warning(f"Failed login attempt for username: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Создание токена доступа
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    logger.info(f"User {form_data.username} logged in successfully")
    return {"access_token": access_token, "token_type": "bearer"}


def generate_unique_short_code(db: Session, length: int = 6) -> str:
    """
    Генерирует уникальный короткий код для ссылки
    
    Args:
        db: Сессия базы данных
        length: Длина короткого кода
        
    Returns:
        Уникальный короткий код
    """
    while True:
        short_code = shortuuid.uuid()[:length]
        db_link = db.query(models.Link).filter(models.Link.short_code == short_code).first()
        if not db_link:
            return short_code

def parse_expiry_date(expires_at: Union[str, datetime, None]) -> Optional[datetime]:
    """
    Преобразует строку даты истечения срока в объект datetime
    
    Args:
        expires_at: Дата истечения срока в виде строки или объекта datetime
        
    Returns:
        Объект datetime или None
    """
    if not expires_at:
        return None
        
    if isinstance(expires_at, datetime):
        return expires_at
        
    try:
        # Обрабатываем ISO формат с учетом часового пояса
        return datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
    except Exception as e:
        logger.error(f"Error parsing expiry date: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")

def check_link_expiry(link: models.Link, db: Session) -> bool:
    """
    Проверяет, не истек ли срок действия ссылки, и обновляет ее статус
    
    Args:
        link: Объект ссылки
        db: Сессия базы данных
        
    Returns:
        True, если срок действия ссылки истек, иначе False
    """
    if link.expires_at and link.expires_at < datetime.now() and link.is_active:
        logger.debug(f"Link {link.short_code} has expired, marking as inactive")
        link.is_active = False
        db.commit()
        return True
    return False

# Endpoint для создания короткой ссылки
@app.post("/links/shorten", response_model=schemas.LinkResponse)
def create_short_link(
    link: schemas.LinkCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(auth.get_optional_user)
) -> models.Link:
    """
    Создание короткой ссылки
    
    Args:
        link: Данные для создания ссылки
        background_tasks: Менеджер фоновых задач
        db: Сессия базы данных
        current_user: Текущий пользователь (опционально)
        
    Returns:
        Созданная ссылка
    """
    logger.debug(f"Received request to create short link: {link.original_url}")
    
    try:
        # Определение короткого кода
        if link.custom_alias:
            logger.debug(f"Custom alias provided: {link.custom_alias}")
            db_link = db.query(models.Link).filter(models.Link.short_code == link.custom_alias).first()
            if db_link:
                logger.warning(f"Custom alias already in use: {link.custom_alias}")
                raise HTTPException(status_code=400, detail="Custom alias already in use")
            short_code = link.custom_alias
        else:
            short_code = generate_unique_short_code(db)
            logger.debug(f"Generated short code: {short_code}")

        # Парсинг даты истечения срока
        expires_at = parse_expiry_date(link.expires_at)
        
        # Создание новой ссылки
        db_link = models.Link(
            short_code=short_code,
            original_url=str(link.original_url),
            custom_alias=link.custom_alias,
            expires_at=expires_at,
            owner_id=current_user.id if current_user else None
        )
        
        try:
            db.add(db_link)
            db.commit()
            db.refresh(db_link)
            logger.info(f"Link created successfully: {short_code}")
            
            # Кэширование ссылки
            cache.set_link_cache(short_code, str(link.original_url))
            
            # Запуск фоновой задачи очистки
            background_tasks.add_task(bg_tasks.cleanup_expired_links, db)
            
            return db_link
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating link: {str(e)}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail="Error creating link")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error")



@app.get("/healthz")
async def health_check() -> Dict[str, str]:
    """
    Эндпоинт для проверки работоспособности сервиса
    """
    # Проверка базы данных
    try:
        db = next(get_db())
        db.execute(text("SELECT 1")).fetchone()
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        db_status = "unhealthy"
    
    # Проверка Redis
    try:
        if cache.redis_client and cache.redis_client.ping():
            redis_status = "healthy"
        else:
            redis_status = "unhealthy"
    except Exception as e:
        logger.error(f"Redis health check failed: {str(e)}")
        redis_status = "unhealthy"
    
    # Определение общего статуса
    is_healthy = db_status == "healthy"
    status_code = 200 if is_healthy else 503
    
    response = {
        "status": "healthy" if is_healthy else "unhealthy", 
        "database": db_status,
        "redis": redis_status
    }
    
    return JSONResponse(content=response, status_code=status_code)

# Endpoint для поиска ссылки по оригинальному URL
@app.get("/links/search")
def search_by_original_url(
    original_url: str, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(auth.get_current_active_user)
) -> Dict[str, Any]:
    """
    Поиск ссылки по оригинальному URL
    
    Args:
        original_url: Оригинальный URL для поиска
        db: Сессия базы данных
        current_user: Текущий пользователь
        
    Returns:
        Информация о найденной ссылке
    """
    logger.debug(f"Searching for link with original URL: {original_url}")

    # Оптимизированный запрос с фильтрацией по пользователю и URL
    link = db.query(models.Link).filter(
        models.Link.owner_id == current_user.id,
        models.Link.original_url == original_url,
        models.Link.is_active == True
    ).first()
    
    if link:
        logger.debug(f"Found matching link: {link.short_code}")
        return {
            "short_code": link.short_code,
            "original_url": link.original_url,
            "created_at": link.created_at
        }
    
    logger.warning(f"No link found for URL: {original_url}")
    raise HTTPException(status_code=404, detail="Link not found")

# Endpoint для получения истории истекших ссылок
@app.get("/expired-links")
def get_expired_links(
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(auth.get_current_active_user)
) -> List[Dict[str, Any]]:
    """
    Получение списка истекших ссылок пользователя
    
    Args:
        db: Сессия базы данных
        current_user: Текущий пользователь
        
    Returns:
        Список истекших ссылок
    """
    logger.debug(f"Getting expired links for user: {current_user.username}")
    
    # Получаем неактивные ссылки
    inactive_links = db.query(models.Link).filter(
        models.Link.owner_id == current_user.id,
        models.Link.is_active == False
    ).all()
    
    logger.debug(f"Found {len(inactive_links)} inactive links")
    
    # Получаем активные ссылки с истекшим сроком
    active_expired_links = db.query(models.Link).filter(
        models.Link.owner_id == current_user.id,
        models.Link.is_active == True,
        models.Link.expires_at.isnot(None),
        models.Link.expires_at < datetime.now()
    ).all()
    
    logger.debug(f"Found {len(active_expired_links)} active links with expired dates")
    
    # Обновляем статус активных истекших ссылок
    if active_expired_links:
        for link in active_expired_links:
            link.is_active = False
            
            # Удаляем из кэша
            cache.delete_link_cache(link.short_code)
        
        db.commit()
        logger.debug("Updated status of expired links")
    
    # Объединяем все истекшие ссылки
    all_expired = inactive_links + active_expired_links
    
    if not all_expired:
        logger.debug("No expired links found")
        return []
    
    # Формируем результат
    result = []
    for link in all_expired:
        result.append({
            "short_code": link.short_code,
            "original_url": link.original_url,
            "created_at": link.created_at,
            "expired_at": link.expires_at or datetime.now(),
            "total_clicks": link.clicks
        })
    
    return result


@app.post("/links/cleanup", response_model=Dict[str, str])
def cleanup_unused_links(
    days: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
) -> Dict[str, str]:
    """
    Очистка неиспользуемых ссылок
    
    Args:
        days: Количество дней неактивности
        background_tasks: Менеджер фоновых задач
        db: Сессия базы данных
        current_user: Текущий пользователь
        
    Returns:
        Сообщение о результате операции
    """
    logger.debug(f"Setting up cleanup for links unused for {days} days")
    
    if days < 1:
        raise HTTPException(status_code=400, detail="Days must be a positive integer")

    cutoff_date = datetime.now() - timedelta(days=days)
    
    try:
        # Находим неиспользуемые ссылки
        unused_links = db.query(models.Link).filter(
            models.Link.owner_id == current_user.id,
            models.Link.is_active == True,
            (models.Link.last_used.is_(None) & (models.Link.created_at < cutoff_date)) |
            (models.Link.last_used < cutoff_date)
        ).all()

        # Деактивируем неиспользуемые ссылки
        for link in unused_links:
            link.is_active = False
            # Удаляем из кэша
            cache.delete_link_cache(link.short_code)
        
        db.commit()
        
        logger.info(f"Deactivated {len(unused_links)} unused links")
        return {"message": f"Deactivated {len(unused_links)} links unused for {days} days"}
    
    except Exception as e:
        logger.error(f"Error cleaning up unused links: {str(e)}")
        logger.error(traceback.format_exc())
        db.rollback()
        raise HTTPException(status_code=500, detail="Error cleaning up links")

# Endpoint для получения информации о ссылке
@app.get("/links/{short_code}", response_model=schemas.LinkStats)
def get_link_info(short_code: str, db: Session = Depends(get_db)) -> schemas.LinkStats:
    """
    Получение информации о ссылке
    
    Args:
        short_code: Короткий код ссылки
        db: Сессия базы данных
        
    Returns:
        Статистика по ссылке
    """
    logger.debug(f"Getting info for link: {short_code}")
    
    # Проверяем кэш
    stats = cache.get_stats_cache(short_code)
    
    if not stats:
        logger.debug("Cache miss, querying database")
        # Если нет в кэше, запрашиваем из БД
        db_link = db.query(models.Link).filter(
            models.Link.short_code == short_code,
            models.Link.is_active == True
        ).first()
        
        if not db_link:
            logger.warning(f"Link not found: {short_code}")
            raise HTTPException(status_code=404, detail="Link not found")

        # Формируем статистику и кэшируем
        stats = {
            "original_url": db_link.original_url,
            "short_code": db_link.short_code,
            "created_at": db_link.created_at.isoformat(),
            "clicks": db_link.clicks,
            "last_used": db_link.last_used.isoformat() if db_link.last_used else None,
            "expires_at": db_link.expires_at.isoformat() if db_link.expires_at else None,
            "owner_id": db_link.owner_id
        }
        cache.set_stats_cache(short_code, stats)
        
        return db_link
    else:
        logger.debug("Cache hit, using cached data")
        # Если есть в кэше, преобразуем данные в модель
        return schemas.LinkStats(
            original_url=stats["original_url"],
            short_code=stats["short_code"],
            created_at=datetime.fromisoformat(stats["created_at"]),
            clicks=stats["clicks"],
            last_used=datetime.fromisoformat(stats["last_used"]) if stats["last_used"] else None,
            expires_at=datetime.fromisoformat(stats["expires_at"]) if stats["expires_at"] else None,
            owner_id=stats["owner_id"]
        )

# Endpoint для получения статистики по ссылке
@app.get("/links/{short_code}/stats", response_model=schemas.LinkStats)
def get_link_stats(short_code: str, db: Session = Depends(get_db)) -> schemas.LinkStats:
    """
    Получение статистики по ссылке
    
    Args:
        short_code: Короткий код ссылки
        db: Сессия базы данных
        
    Returns:
        Статистика по ссылке
    """
    return get_link_info(short_code, db)


# Endpoint для обновления ссылки
@app.put("/links/{short_code}", response_model=schemas.LinkResponse)
def update_link(
    short_code: str,
    link_update: schemas.LinkUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
) -> models.Link:
    """
    Обновление ссылки
    
    Args:
        short_code: Короткий код ссылки
        link_update: Данные для обновления
        db: Сессия базы данных
        current_user: Текущий пользователь
        
    Returns:
        Обновленная ссылка
    """
    logger.debug(f"Updating link: {short_code}")
    
    # Находим ссылку
    db_link = db.query(models.Link).filter(
        models.Link.short_code == short_code,
        models.Link.is_active == True
    ).first()
    
    if not db_link:
        logger.warning(f"Link not found: {short_code}")
        raise HTTPException(status_code=404, detail="Link not found")

    # Проверяем права доступа
    if db_link.owner_id != current_user.id:
        logger.warning(f"Unauthorized update attempt for link {short_code} by user {current_user.username}")
        raise HTTPException(status_code=403, detail="Not authorized to update this link")

    try:
        # Удаляем старый кэш
        cache.delete_link_cache(short_code)
        
        # Обновляем оригинальный URL
        if link_update.original_url:
            logger.debug(f"Updating original URL: {link_update.original_url}")
            db_link.original_url = str(link_update.original_url)
        
        # Обновляем короткий код (пользовательский алиас)
        if link_update.custom_alias:
            logger.debug(f"Updating custom alias: {link_update.custom_alias}")
            # Проверяем, не занят ли новый алиас
            existing_link = db.query(models.Link).filter(
                models.Link.short_code == link_update.custom_alias,
                models.Link.id != db_link.id
            ).first()
            
            if existing_link:
                logger.warning(f"Custom alias already in use: {link_update.custom_alias}")
                raise HTTPException(status_code=400, detail="Custom alias already in use")

            old_short_code = db_link.short_code
            db_link.short_code = link_update.custom_alias
            db_link.custom_alias = link_update.custom_alias

            # Удаляем кэш для старого short_code
            cache.delete_link_cache(old_short_code)
        
        # Обновляем срок действия
        if link_update.expires_at:
            logger.debug(f"Updating expiry date: {link_update.expires_at}")
            db_link.expires_at = link_update.expires_at
        
        # Сохраняем изменения
        db.commit()
        db.refresh(db_link)
        
        # Обновляем кэш
        cache.set_link_cache(db_link.short_code, db_link.original_url)
        
        logger.info(f"Link updated successfully: {db_link.short_code}")
        return db_link
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating link: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Error updating link")

@app.delete("/links/{short_code}", status_code=204)
def delete_link(
    short_code: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
) -> None:
    """
    Удаление ссылки
    
    Args:
        short_code: Короткий код ссылки
        db: Сессия базы данных
        current_user: Текущий пользователь
    """
    logger.debug(f"Deleting link: {short_code}")
    
    # Находим ссылку
    db_link = db.query(models.Link).filter(
        models.Link.short_code == short_code,
        models.Link.is_active == True
    ).first()
    
    if not db_link:
        logger.warning(f"Link not found: {short_code}")
        raise HTTPException(status_code=404, detail="Link not found")

    # Проверяем права доступа
    if db_link.owner_id != current_user.id:
        logger.warning(f"Unauthorized delete attempt for link {short_code} by user {current_user.username}")
        raise HTTPException(status_code=403, detail="Not authorized to delete this link")

    try:
        # Деактивируем ссылку
        db_link.is_active = False
        db.commit()
        
        # Удаляем из кэша
        cache.delete_link_cache(short_code)
        
        logger.info(f"Link deleted successfully: {short_code}")
        return None
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting link: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Error deleting link")

@app.get("/docs-v2", response_class=HTMLResponse)
async def custom_swagger_ui_html():
    return """
    <!DOCTYPE html>
    <html>
      <head>
        <title>URL Shortener API Documentation</title>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@4.5.0/swagger-ui.css" />
        <style>
          html { box-sizing: border-box; overflow: -moz-scrollbars-vertical; overflow-y: scroll; }
          *, *:before, *:after { box-sizing: inherit; }
          body { margin: 0; background: #fafafa; }
          .swagger-ui .topbar { display: none; }
        </style>
      </head>
      <body>
        <div id="swagger-ui"></div>
        <script src="https://unpkg.com/swagger-ui-dist@4.5.0/swagger-ui-bundle.js" charset="UTF-8"></script>
        <script>
          window.onload = function() {
            // Функция для преобразования OpenAPI 3.1.0 в 3.0.0
            function convertOpenApiVersion(spec) {
              if (spec.openapi && spec.openapi.startsWith('3.1')) {
                spec.openapi = '3.0.0';
                
                // Обработка типов данных, которые изменились в 3.1
                if (spec.components && spec.components.schemas) {
                  Object.values(spec.components.schemas).forEach(schema => {
                    if (schema.type === 'null' || (Array.isArray(schema.type) && schema.type.includes('null'))) {
                      schema.nullable = true;
                      if (Array.isArray(schema.type)) {
                        schema.type = schema.type.filter(t => t !== 'null')[0];
                      } else {
                        delete schema.type;
                      }
                    }
                  });
                }
              }
              return spec;
            }
            
            // Загрузка спецификации и преобразование версии
            fetch("/openapi.json")
              .then(response => response.json())
              .then(spec => {
                const convertedSpec = convertOpenApiVersion(spec);
                
                // Инициализация Swagger UI с преобразованной спецификацией
                const ui = SwaggerUIBundle({
                  spec: convertedSpec,
                  dom_id: '#swagger-ui',
                  deepLinking: true,
                  presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIBundle.SwaggerUIStandalonePreset
                  ],
                  layout: "BaseLayout"
                });
              })
              .catch(error => {
                console.error("Error loading OpenAPI spec:", error);
                document.getElementById('swagger-ui').innerHTML = 
                  '<div style="padding: 20px; color: red;">' +
                  '<h2>Error Loading API Documentation</h2>' +
                  '<p>Could not load the OpenAPI specification.</p>' +
                  '<p>Error details: ' + error.message + '</p>' +
                  '</div>';
              });
          };
        </script>
      </body>
    </html>
    """


# Перенаправление по короткой ссылке (должно быть ПОСЛЕ всех специфичных маршрутов)
@app.get("/{short_code}", response_class=RedirectResponse, status_code=307)
def redirect_to_url(short_code: str, db: Session = Depends(get_db)) -> str:
    """
    Перенаправление по короткой ссылке
    
    Args:
        short_code: Короткий код ссылки
        db: Сессия базы данных
        
    Returns:
        Оригинальный URL для перенаправления
    """
    logger.debug(f"Redirecting short code: {short_code}")

    # Сначала проверяем кэш
    original_url = cache.get_link_cache(short_code)
    
    # Находим ссылку в БД в любом случае, чтобы обновить счетчик
    link = db.query(models.Link).filter(
        models.Link.short_code == short_code,
        models.Link.is_active == True
    ).first()
    
    if not link:
        logger.warning(f"Link not found: {short_code}")
        raise HTTPException(status_code=404, detail="Link not found")

    # Проверяем срок действия
    if check_link_expiry(link, db):
        logger.warning(f"Link expired: {short_code}")
        raise HTTPException(status_code=404, detail="Link has expired")

    if not original_url:
        # Если нет в кэше, берем из БД и кэшируем
        original_url = link.original_url
        cache.set_link_cache(short_code, original_url)
    
    try:
        # Обновляем счетчик и время последнего использования
        link.clicks += 1
        link.last_used = datetime.now()
        db.commit()
        
        # Обновляем кэш статистики, если он есть
        cache.increment_link_clicks(short_code)
        
        logger.debug(f"Redirecting to: {original_url}")
        return original_url
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating click stats: {str(e)}")
        # Продолжаем перенаправление, даже если не удалось обновить статистику
        return original_url

