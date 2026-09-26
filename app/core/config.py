from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "EVE Healthcare API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # Security
    SECRET_KEY: str = "super-secret-key-change-in-production-eve-healthcare-2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # Database
    DATABASE_URL: str = "sqlite:///./eve_healthcare.db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_ENABLED: bool = True
    CACHE_DEFAULT_TTL: int = 300  # 5 minutes
    
    # Webhook
    WEBHOOK_SECRET: str = "whsec_simulated_eve_secret_key_8921"
    
    # Rate Limiting (requests per minute)
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    @field_validator("DATABASE_URL", mode="after")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        import os
        # Vercel serverless environment root filesystem is read-only; use /tmp for default SQLite
        if os.environ.get("VERCEL") and v.startswith("sqlite:///."):
            return "sqlite:////tmp/eve_healthcare.db"
        return v

    @field_validator("CACHE_ENABLED", mode="after")
    @classmethod
    def validate_cache_enabled(cls, v: bool) -> bool:
        import os
        if os.environ.get("VERCEL") and not os.environ.get("REDIS_URL"):
            return False
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
