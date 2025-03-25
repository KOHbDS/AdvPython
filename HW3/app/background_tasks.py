from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from . import models
import logging

logger = logging.getLogger(__name__)

def cleanup_expired_links(db: Session) -> None:
    """Перемещение истекших ссылок в архив"""
    try:
        # Находим все истекшие ссылки
        expired_links = db.query(models.Link).filter(
            models.Link.expires_at.isnot(None),
            models.Link.expires_at < datetime.now(),
            models.Link.is_active == True
        ).all()
        
        # Перемещаем их в таблицу истекших ссылок и деактивируем
        for link in expired_links:
            expired_link = models.ExpiredLink(
                short_code=link.short_code,
                original_url=link.original_url,
                created_at=link.created_at,
                expired_at=datetime.now(),
                total_clicks=link.clicks,
                owner_id=link.owner_id
            )
            db.add(expired_link)
            link.is_active = False
        
        db.commit()
        logger.info(f"Moved {len(expired_links)} expired links to archive")
    except Exception as e:
        db.rollback()
        logger.error(f"Error cleaning up expired links: {str(e)}")


def cleanup_unused_links(db: Session, days: int = 90) -> None:
    """Перемещение неиспользуемых ссылок в архив"""
    try:
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Находим все неиспользуемые ссылки
        unused_links = db.query(models.Link).filter(
            (models.Link.last_used.is_(None) & (models.Link.created_at < cutoff_date)) |
            (models.Link.last_used < cutoff_date),
            models.Link.is_active == True
        ).all()
        
        # Деактивируем ссылки
        for link in unused_links:
            link.is_active = False
        
        db.commit()
        logger.info(f"Deactivated {len(unused_links)} unused links")
    except Exception as e:
        db.rollback()
        logger.error(f"Error cleaning up unused links: {str(e)}")

