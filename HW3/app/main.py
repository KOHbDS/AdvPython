import logging
from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks, Request
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List, Optional, Union
from datetime import datetime, timedelta
import shortuuid
import traceback

# Импорты из вашего проекта
from . import models, schemas, database, auth, cache, background_tasks as bg_tasks
from .database import engine, get_db

# Настройка логирования в файл
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("debug.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Логируем запуск приложения
logger.info("Starting URL Shortener API")

# Создаем таблицы в базе данных
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="URL Shortener API",
    description="API for shortening URLs with statistics and user management",
    version="1.0.0"
)

# Middleware для обработки исключений
@app.middleware("http")
async def log_exceptions(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error", "error": str(e)}
        )

# Обработчики событий
@app.on_event("startup")
async def startup_event():
    logger.info("Application startup")
    try:
        # Проверка подключения к базе данных
        db = next(get_db())
        result = db.execute("SELECT 1").fetchone()
        logger.info(f"Database connection successful: {result}")
        
        # Проверка подключения к Redis
        try:
            redis_result = cache.redis_client.ping()
            logger.info(f"Redis connection successful: {redis_result}")
        except Exception as e:
            logger.error(f"Redis connection failed: {str(e)}")
    except Exception as e:
        logger.error(f"Startup check failed: {str(e)}")
        logger.error(traceback.format_exc())

# Endpoint для регистрации пользователя
@app.post("/users/", response_model=schemas.UserResponse)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = auth.get_password_hash(user.password)
    db_user = models.User(username=user.username, email=user.email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# Endpoint для получения токена доступа
@app.post("/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = auth.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# Endpoint для создания короткой ссылки
@app.post("/links/shorten", response_model=schemas.LinkResponse)
def create_short_link(
    link: schemas.LinkCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(auth.get_optional_user)
):
    logger.debug(f"Received request to create short link: {link}")
    
    try:
        # Проверка кастомного alias, если он предоставлен
        if link.custom_alias:
            logger.debug(f"Custom alias provided: {link.custom_alias}")
            db_link = db.query(models.Link).filter(models.Link.short_code == link.custom_alias).first()
            if db_link:
                logger.warning(f"Custom alias already in use: {link.custom_alias}")
                raise HTTPException(status_code=400, detail="Custom alias already in use")
            short_code = link.custom_alias
        else:
            # Генерация уникального короткого кода
            logger.debug("Generating unique short code")
            while True:
                short_code = shortuuid.uuid()[:6]
                db_link = db.query(models.Link).filter(models.Link.short_code == short_code).first()
                if not db_link:
                    break
            logger.debug(f"Generated short code: {short_code}")
        
        # Обработка даты истечения срока действия
        expires_at = None
        if link.expires_at:
            logger.debug(f"Expiry date provided: {link.expires_at}")
            try:
                # Если дата передана как строка, преобразуем ее
                if isinstance(link.expires_at, str):
                    expires_at = datetime.fromisoformat(link.expires_at.replace('Z', '+00:00'))
                else:
                    expires_at = link.expires_at
                logger.debug(f"Parsed expiry date: {expires_at}")
            except Exception as e:
                logger.error(f"Error parsing expiry date: {str(e)}")
                raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
        
        # Создание новой ссылки
        logger.debug("Creating link in database")
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
        except Exception as e:
            logger.error(f"Database error: {str(e)}")
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        
        # Кэширование ссылки
        try:
            logger.debug(f"Caching link: {short_code}")
            cache.set_link_cache(short_code, str(link.original_url))
        except Exception as e:
            logger.error(f"Caching error (non-critical): {str(e)}")
            # Не прерываем выполнение, если кэширование не удалось
        
        # Запуск фоновой задачи для очистки истекших ссылок
        try:
            logger.debug("Starting background task for cleanup")
            background_tasks.add_task(bg_tasks.cleanup_expired_links, db)
        except Exception as e:
            logger.error(f"Background task error (non-critical): {str(e)}")
            # Не прерываем выполнение, если запуск фоновой задачи не удался
        
        return db_link
    except HTTPException:
        # Пробрасываем HTTP исключения
        raise
    except Exception as e:
        # Логируем любые другие ошибки
        logger.error(f"Unexpected error creating link: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error creating link: {str(e)}")

def check_link_expiry(link: models.Link, db: Session) -> bool:
    """Проверяет, не истек ли срок действия ссылки, и обновляет ее статус"""
    if link.expires_at and link.expires_at < datetime.now() and link.is_active:
        logger.debug(f"Link {link.short_code} has expired, marking as inactive")
        link.is_active = False
        db.commit()
        return True
    return False

# ВАЖНО: Перемещаем специфические маршруты выше общего маршрута {short_code}

# Endpoint для поиска ссылки по оригинальному URL
@app.get("/search-url")
def search_url(url: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    """Простой эндпоинт для поиска ссылки по URL"""
    logger.debug(f"Searching for link with URL: {url}")
    
    # Получаем все ссылки пользователя
    user_links = db.query(models.Link).filter(
        models.Link.owner_id == current_user.id
    ).all()
    
    for link in user_links:
        logger.debug(f"Comparing: DB URL='{link.original_url}' vs Search URL='{url}'")
        if link.original_url == url:
            return {
                "short_code": link.short_code,
                "original_url": link.original_url,
                "created_at": link.created_at
            }
    
    raise HTTPException(status_code=404, detail="Link not found")

# Endpoint для получения истории истекших ссылок
@app.get("/expired-links")
def get_expired_links(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    """Получение списка истекших ссылок пользователя"""
    logger.debug(f"Getting expired links for user: {current_user.username}")
    
    # Находим все неактивные ссылки пользователя
    inactive_links = db.query(models.Link).filter(
        models.Link.owner_id == current_user.id,
        models.Link.is_active == False
    ).all()
    
    logger.debug(f"Found {len(inactive_links)} inactive links")
    
    # Также проверяем активные ссылки с истекшим сроком действия
    active_links = db.query(models.Link).filter(
        models.Link.owner_id == current_user.id,
        models.Link.is_active == True,
        models.Link.expires_at.isnot(None),
        models.Link.expires_at < datetime.now()
    ).all()
    
    logger.debug(f"Found {len(active_links)} active links with expired dates")
    
    # Помечаем активные ссылки с истекшим сроком как неактивные
    for link in active_links:
        link.is_active = False
    
    if active_links:
        db.commit()
        logger.debug("Updated status of expired links")
    
    # Объединяем результаты
    all_expired = inactive_links + active_links
    
    if not all_expired:
        logger.debug("No expired links found")
        return []
    
    # Преобразуем в формат ответа
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

# Endpoint для настройки автоматического удаления
@app.post("/links/cleanup", response_model=dict)
def cleanup_unused_links(
    days: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    logger.debug(f"Setting up cleanup for links unused for {days} days")
    
    if days < 1:
        raise HTTPException(status_code=400, detail="Days must be a positive integer")
    
    # Находим и деактивируем ссылки, не использовавшиеся более указанного количества дней
    cutoff_date = datetime.now() - timedelta(days=days)
    
    try:
        # Выполняем очистку непосредственно здесь вместо фоновой задачи
        unused_links = db.query(models.Link).filter(
            models.Link.owner_id == current_user.id,
            models.Link.is_active == True,
            (models.Link.last_used.is_(None) & (models.Link.created_at < cutoff_date)) |
            (models.Link.last_used < cutoff_date)
        ).all()
        
        # Деактивируем найденные ссылки
        for link in unused_links:
            link.is_active = False
        
        db.commit()
        
        logger.info(f"Deactivated {len(unused_links)} unused links")
        return {"message": f"Deactivated {len(unused_links)} links unused for {days} days"}
    
    except Exception as e:
        logger.error(f"Error cleaning up unused links: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error cleaning up links: {str(e)}")

# Endpoint для поиска ссылки по оригинальному URL (альтернативный маршрут)
@app.get("/links/search")
def search_by_original_url(original_url: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    logger.debug(f"Searching for link with original URL: {original_url}")
    
    # Выводим все ссылки пользователя для отладки
    all_links = db.query(models.Link).filter(
        models.Link.owner_id == current_user.id,
        models.Link.is_active == True
    ).all()
    
    logger.debug(f"User has {len(all_links)} active links")
    for link in all_links:
        logger.debug(f"Link: {link.short_code}, URL: {link.original_url}")
        # Проверяем совпадение URL
        if link.original_url == original_url:
            logger.debug(f"Found matching link: {link.short_code}")
            return {
                "short_code": link.short_code,
                "original_url": link.original_url,
                "created_at": link.created_at
            }
    
    logger.warning(f"No link found for URL: {original_url}")
    raise HTTPException(status_code=404, detail="Link not found")

# Endpoint для получения информации о ссылке
@app.get("/links/{short_code}", response_model=schemas.LinkStats)
def get_link_info(short_code: str, db: Session = Depends(get_db)):
    # Проверяем кэш
    stats = cache.get_stats_cache(short_code)
    
    if not stats:
        # Если нет в кэше, ищем в базе данных
        db_link = db.query(models.Link).filter(
            models.Link.short_code == short_code,
            models.Link.is_active == True
        ).first()
        
        if not db_link:
            raise HTTPException(status_code=404, detail="Link not found")
        
        # Кэшируем статистику
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
        # Преобразуем даты из строк в объекты datetime
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
def get_link_stats(short_code: str, db: Session = Depends(get_db)):
    # Используем тот же метод, что и для получения информации о ссылке
    return get_link_info(short_code, db)

# Endpoint для обновления ссылки
@app.put("/links/{short_code}", response_model=schemas.LinkResponse)
def update_link(
    short_code: str,
    link_update: schemas.LinkUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    db_link = db.query(models.Link).filter(
        models.Link.short_code == short_code,
        models.Link.is_active == True
    ).first()
    
    if not db_link:
        raise HTTPException(status_code=404, detail="Link not found")
    
    # Проверяем, принадлежит ли ссылка текущему пользователю
    if db_link.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this link")
    
    # Обновляем поля, если они предоставлены
    if link_update.original_url:
        db_link.original_url = str(link_update.original_url)
    
    if link_update.custom_alias:
        # Проверяем, не занят ли новый alias
        existing_link = db.query(models.Link).filter(
            models.Link.short_code == link_update.custom_alias,
            models.Link.id != db_link.id
        ).first()
        
        if existing_link:
            raise HTTPException(status_code=400, detail="Custom alias already in use")
        
        # Обновляем короткий код
        old_short_code = db_link.short_code
        db_link.short_code = link_update.custom_alias
        db_link.custom_alias = link_update.custom_alias
        
        # Удаляем старый кэш
        cache.delete_link_cache(old_short_code)
    
    if link_update.expires_at:
        db_link.expires_at = link_update.expires_at
    
    db.commit()
    db.refresh(db_link)
    
    # Обновляем кэш
    cache.delete_link_cache(db_link.short_code)
    cache.set_link_cache(db_link.short_code, db_link.original_url)
    
    return db_link

# Endpoint для удаления ссылки
@app.delete("/links/{short_code}", status_code=204)
def delete_link(
    short_code: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    db_link = db.query(models.Link).filter(
        models.Link.short_code == short_code,
        models.Link.is_active == True
    ).first()
    
    if not db_link:
        raise HTTPException(status_code=404, detail="Link not found")
    
    # Проверяем, принадлежит ли ссылка текущему пользователю
    if db_link.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this link")
    
    # Деактивируем ссылку (soft delete)
    db_link.is_active = False
    db.commit()
    
    # Удаляем из кэша
    cache.delete_link_cache(short_code)
    
    return None

# Перенаправление по короткой ссылке (должно быть ПОСЛЕ всех специфичных маршрутов)
@app.get("/{short_code}", response_class=RedirectResponse, status_code=307)
def redirect_to_url(short_code: str, db: Session = Depends(get_db)):
    """Перенаправление по короткой ссылке с проверкой срока действия"""
    logger.debug(f"Redirecting short code: {short_code}")
    
    # Получаем ссылку из базы данных
    link = db.query(models.Link).filter(
        models.Link.short_code == short_code
    ).first()
    
    if not link:
        logger.warning(f"Link not found: {short_code}")
        raise HTTPException(status_code=404, detail="Link not found")
    
    # Проверяем, не истек ли срок действия
    if check_link_expiry(link, db):
        logger.warning(f"Link expired: {short_code}")
        raise HTTPException(status_code=404, detail="Link has expired")
    
    # Обновляем статистику
    link.clicks += 1
    link.last_used = datetime.now()
    db.commit()
    
    logger.debug(f"Redirecting to: {link.original_url}")
    return link.original_url

# Middleware для логирования запросов
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.debug(f"Request: {request.method} {request.url}")
    try:
        response = await call_next(request)
        logger.debug(f"Response: {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutdown")

# Простой эндпоинт для тестирования без БД
@app.post("/test/shorten")
def test_shorten_link(link_request: dict):
    try:
        logger.debug(f"Received test link request: {link_request}")
        
        # Извлекаем данные из запроса
        original_url = link_request.get("original_url")
        custom_alias = link_request.get("custom_alias")
        expires_at_str = link_request.get("expires_at")
        
        if not original_url:
            return {"error": "Original URL is required"}
        
        # Генерируем короткий код
        short_code = custom_alias or shortuuid.uuid()[:6]
        
        # Обрабатываем expires_at
        expires_at = None
        if expires_at_str:
            try:
                # Преобразуем строку в datetime
                expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
                logger.debug(f"Parsed expires_at: {expires_at}")
            except Exception as e:
                logger.error(f"Error parsing expires_at: {str(e)}")
                return {"error": f"Invalid date format: {str(e)}"}
        
        # Возвращаем результат
        return {
            "short_code": short_code,
            "original_url": original_url,
            "created_at": datetime.now().isoformat(),
            "expires_at": expires_at.isoformat() if expires_at else None
        }
    except Exception as e:
        logger.error(f"Error in test endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        return {"error": str(e)}
