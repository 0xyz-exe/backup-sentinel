from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "Backup Sentinel"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    
    # Security
    SECRET_KEY: str = "sentinel-super-secret-key-change-in-production-min-32-chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # Database (SQLite default for local dev, PostgreSQL for prod)
    DATABASE_URL: str = "sqlite:///./sentinel.db"
    
    # Storage and Sandbox
    ALLOWED_STORAGE_ROOTS: List[str] = ["./fixtures", "./backups", "/var/backups", "C:/Users/wondr/HermesWorkspace/backup-sentinel/fixtures"]
    MAX_BACKUP_SIZE_BYTES: int = 10 * 1024 * 1024 * 1024  # 10 GB limit
    MAX_DECOMPRESSED_RATIO: float = 100.0  # Zip-bomb protection
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000", "http://127.0.0.1:3000",
        "http://localhost:3050", "http://127.0.0.1:3050",
        "http://localhost:8000"
    ]
    
    # Docker Recovery
    ENABLE_DOCKER_RECOVERY: bool = True
    DOCKER_CONTAINER_TIMEOUT_SECONDS: int = 60
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
