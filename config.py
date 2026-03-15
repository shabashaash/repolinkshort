from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    DATABASE_URL: str = Field(default="")
    REDIS_URL: str = Field(default="")
    SECRET_KEY: str = Field(default="")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    DEFAULT_LINK_EXPIRE_DAYS: int = 30
    UNUSED_LINK_DELETE_DAYS: int = 90
    
    class Config:
        env_file: str = ".env"
        extra: str = "ignore"

settings = Settings()