from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./dtaas.db"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # CORS
    cors_origins: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]
    
    # Logging
    log_level: str = "INFO"
    
    # Celery
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    
    class Config:
        env_file = ".env"


settings = Settings()

