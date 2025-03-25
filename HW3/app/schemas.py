from pydantic import BaseModel, HttpUrl, validator
from typing import Optional, Union
from datetime import datetime

# Модели для пользователей
class UserBase(BaseModel):
    username: str
    email: str

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    created_at: datetime
    
    class Config:
        orm_mode = True

# Модели для ссылок
class LinkBase(BaseModel):
    original_url: str  # Используем строку вместо HttpUrl

class LinkCreate(LinkBase):
    custom_alias: Optional[str] = None
    expires_at: Optional[Union[str, datetime]] = None  # Позволяем использовать как строку, так и datetime

class LinkUpdate(BaseModel):
    original_url: Optional[HttpUrl] = None
    custom_alias: Optional[str] = None
    expires_at: Optional[datetime] = None

class LinkResponse(BaseModel):
    short_code: str
    original_url: str
    created_at: datetime
    
    class Config:
        orm_mode = True

class LinkStats(LinkResponse):
    clicks: int
    last_used: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    owner_id: Optional[int] = None
    
    class Config:
        orm_mode = True

# Модели для токенов
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# Модель для истекших ссылок
class ExpiredLinkResponse(BaseModel):
    short_code: str
    original_url: HttpUrl
    created_at: datetime
    expired_at: datetime
    total_clicks: int
    
    class Config:
        orm_mode = True
