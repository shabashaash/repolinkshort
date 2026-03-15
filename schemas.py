from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime

class UserCreate(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    is_active: bool
    is_superuser: bool
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class LinkCreate(BaseModel):
    original_url: str
    custom_alias: Optional[str] = None
    project: Optional[str] = "default"
    expires_at: Optional[datetime] = None

class LinkUpdate(BaseModel):
    original_url: str

class LinkResponse(BaseModel):
    short_code: str
    original_url: str
    custom_alias: Optional[str] = None
    created_at: datetime
    click_count: int
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class LinkStats(LinkResponse):
    pass

class LinkShortenResponse(BaseModel):
    short_code: str
    short_url: str
    original_url: str