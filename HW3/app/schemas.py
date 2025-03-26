from pydantic import BaseModel, HttpUrl, EmailStr, Field
from typing import Optional, Union, Annotated
from datetime import datetime

# Модели для пользователей
class UserBase(BaseModel):
    username: Annotated[str, Field(min_length=3, max_length=50)]
    email: EmailStr

class UserCreate(UserBase):
    password: Annotated[str, Field(min_length=8)]

class UserResponse(UserBase):
    id: int
    created_at: datetime
    
    model_config = {"from_attributes": True}

# Модели для ссылок
class LinkBase(BaseModel):
    original_url: HttpUrl

class LinkCreate(LinkBase):
    custom_alias: Optional[Annotated[str, Field(min_length=3, max_length=50)]] = None
    expires_at: Optional[Union[str, datetime]] = None

class LinkUpdate(BaseModel):
    original_url: Optional[HttpUrl] = None
    custom_alias: Optional[Annotated[str, Field(min_length=3, max_length=50)]] = None
    expires_at: Optional[datetime] = None

class LinkResponse(BaseModel):
    short_code: str
    original_url: str
    created_at: datetime
    
    model_config = {"from_attributes": True}

class LinkStats(LinkResponse):
    clicks: int
    last_used: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    owner_id: Optional[int] = None
    
    model_config = {"from_attributes": True}

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
    
    model_config = {"from_attributes": True}
