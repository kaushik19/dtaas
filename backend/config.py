from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # Environment
    environment: str = os.getenv("ENVIRONMENT", "development")
    
    # Database
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./dtaas.db")
    
    # Redis
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # API
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "8000"))
    api_reload: bool = os.getenv("API_RELOAD", "false").lower() == "true"
    
    # CORS - Parse comma-separated string from env
    cors_origins: List[str] = os.getenv(
        "CORS_ORIGINS", 
        "http://localhost:5173,http://localhost:3000"
    ).split(",")
    
    # Security
    secret_key: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    
    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Celery
    celery_broker_url: str = os.getenv("CELERY_BROKER_URL", redis_url)
    celery_result_backend: str = os.getenv("CELERY_RESULT_BACKEND", redis_url)
    
    # WebSocket
    websocket_broadcast_interval: float = float(os.getenv("WEBSOCKET_BROADCAST_INTERVAL", "1.0"))
    
    class Config:
        env_file = ".env"
    
    def is_production(self) -> bool:
        return self.environment.lower() == "production"
    
    def is_development(self) -> bool:
        return self.environment.lower() == "development"


settings = Settings()

