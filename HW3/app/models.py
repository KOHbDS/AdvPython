from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import List, Optional

from .database import Base

class User(Base):
    __tablename__ = "users"
    __allow_unmapped__ = True

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    email = Column(String(100), unique=True, index=True)
    hashed_password = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    links = relationship("Link", back_populates="owner")

class Link(Base):
    __tablename__ = "links"
    __allow_unmapped__ = True

    id = Column(Integer, primary_key=True, index=True)
    short_code = Column(String(20), unique=True, index=True)
    original_url = Column(String(2048))
    custom_alias = Column(String(50), nullable=True)
    clicks = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    owner = relationship("User", back_populates="links")

class ExpiredLink(Base):
    __tablename__ = "expired_links"
    __allow_unmapped__ = True

    id = Column(Integer, primary_key=True, index=True)
    short_code = Column(String(20), index=True)
    original_url = Column(String(2048))
    created_at = Column(DateTime(timezone=True))
    expired_at = Column(DateTime(timezone=True), server_default=func.now())
    total_clicks = Column(Integer, default=0)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    owner = relationship("User")
