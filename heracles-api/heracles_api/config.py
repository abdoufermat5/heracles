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
    DEBUG: bool = True
    SECRET_KEY: str = "heracles-dev-secret-change-in-production"
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    # LDAP (defaults for docker-compose)
    LDAP_URI: str = "ldap://localhost:389"
    LDAP_BASE_DN: str = "dc=heracles,dc=local"
    LDAP_BIND_DN: str = "cn=admin,dc=heracles,dc=local"
    LDAP_BIND_PASSWORD: str = "admin_secret"
    LDAP_USE_TLS: bool = False
    LDAP_POOL_SIZE: int = 10
    LDAP_TIMEOUT: int = 30
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://heracles:heracles_secret@localhost:5432/heracles"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PASSWORD: str = "redis_secret"
    
    # Session
    SESSION_TIMEOUT: int = 3600  # 1 hour
    
    # Password
    PASSWORD_HASH_METHOD: str = "ssha"
    PASSWORD_MIN_LENGTH: int = 8
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # Email Validation (DEBUG mode only)
    ALLOW_TEST_EMAIL_DOMAINS: bool = True  # Allow .local/.test domains in debug mode
    TEST_EMAIL_DOMAINS: List[str] = ["heracles.local", "test.local", "localhost"]
    
    # Plugins
    PLUGINS_ENABLED: List[str] = ["posix", "sudo", "ssh"]
    
    # POSIX Plugin Settings
    POSIX_UID_MIN: int = 10000
    POSIX_UID_MAX: int = 60000
    POSIX_GID_MIN: int = 10000
    POSIX_GID_MAX: int = 60000
    POSIX_DEFAULT_SHELL: str = "/bin/bash"
    POSIX_DEFAULT_HOME_BASE: str = "/home"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
