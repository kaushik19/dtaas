"""
Logging configuration for DTaaS
Provides structured logging for both development and production environments
"""
import logging
import sys
from config import settings


def setup_logging():
    """Setup logging configuration based on environment"""
    
    # Get log level from settings
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    
    # Create formatter
    if settings.is_production():
        # Production: JSON-like structured logging
        formatter = logging.Formatter(
            '{"time": "%(asctime)s", "level": "%(levelname)s", "module": "%(name)s", "message": "%(message)s"}',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        # Development: Human-readable logging
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers
    root_logger.handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler for production
    if settings.is_production():
        file_handler = logging.FileHandler('dtaas.log')
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Set levels for third-party libraries
    logging.getLogger('uvicorn').setLevel(logging.WARNING)
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('celery').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    
    return root_logger


# Initialize logging
logger = setup_logging()

