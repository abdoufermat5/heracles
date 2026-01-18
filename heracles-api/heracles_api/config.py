"""
Heracles API Configuration
==========================

Application settings loaded from environment variables.
"""

from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    # LDAP
    LDAP_URI: str = "ldap://localhost:389"
    LDAP_BASE_DN: str = "dc=example,dc=com"
    LDAP_BIND_DN: str = "cn=admin,dc=example,dc=com"
    LDAP_BIND_PASSWORD: str = ""
    LDAP_USE_TLS: bool = False
    LDAP_POOL_SIZE: int = 10
    LDAP_TIMEOUT: int = 30
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://heracles:heracles@localhost:5432/heracles"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Session
    SESSION_TIMEOUT: int = 3600  # 1 hour
    
    # Password
    PASSWORD_HASH_METHOD: str = "ssha"
    PASSWORD_MIN_LENGTH: int = 8
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
