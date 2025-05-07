"""
Application Configuration
========================

Handles environment variables with fallback defaults.
"""
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:Aa!234567890@127.0.0.1:5432/authentication_service")
    SECRET_KEY: str = os.getenv("SECRET_KEY", None)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_file = ".env"

settings = Settings()