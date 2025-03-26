from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from . import models, cache
import logging
import os
import traceback

logger = logging.getLogger(__name__)

DEFAULT_UNUSED_DAYS = int(os.getenv("DEFAULT_UNUSED_DAYS", "90"))

def cleanup_expired_links(db: Session) -> None:
    """Перемещение истекших ссылок в архив"""
    try:
        logger.debug("Starting cleanup of expired links")
        expired_links = db.query(models.Link).filter(
            models.Link.expires_at.isnot(None),
            models.Link.expires_at < datetime.now(),
            models.Link.is_active == True
        ).all()

        logger.debug(f"Found {len(expired_links)} expired links")
        for link in expired_links:
            logger.debug(f"Processing expired link: {link.short_code}")
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
            
            cache.delete_link_cache(link.short_code)
        
        db.commit()
        logger.info(f"Moved {len(expired_links)} expired links to archive")
    except Exception as e:
        db.rollback()
        logger.error(f"Error cleaning up expired links: {str(e)}")
        logger.error(traceback.format_exc())


def cleanup_unused_links(db: Session, days: int = DEFAULT_UNUSED_DAYS) -> None:
    """Перемещение неиспользуемых ссылок в архив"""
    try:
        logger.debug(f"Starting cleanup of links unused for {days} days")
        cutoff_date = datetime.now() - timedelta(days=days)

        unused_links = db.query(models.Link).filter(
            (models.Link.last_used.is_(None) & (models.Link.created_at < cutoff_date)) |
            (models.Link.last_used < cutoff_date),
            models.Link.is_active == True
        ).all()

        logger.debug(f"Found {len(unused_links)} unused links")
        for link in unused_links:
            logger.debug(f"Deactivating unused link: {link.short_code}")
            link.is_active = False
            cache.delete_link_cache(link.short_code)
        
        db.commit()
        logger.info(f"Deactivated {len(unused_links)} unused links")
    except Exception as e:
        db.rollback()
        logger.error(f"Error cleaning up unused links: {str(e)}")
        logger.error(traceback.format_exc())
