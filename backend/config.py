"""Configuration management for MyPoolr Circles backend."""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env.local or .env
load_dotenv('.env.local')
load_dotenv('.env')


class Settings(BaseSettings):
    """Application settings."""
    
    # Supabase Configuration
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None
    supabase_service_key: Optional[str] = None
    
    # Redis Configuration
    redis_url: str = "redis://localhost:6379/0"
    
    # Celery Configuration
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = True
    
    # Security
    secret_key: Optional[str] = None
    
    class Config:
        env_file = [".env.local", ".env"]  # Try .env.local first, then .env
        case_sensitive = False
        
    def __init__(self, **kwargs):
        # Manually load environment variables with proper mapping
        env_mapping = {
            'REDIS_URL': 'redis_url',
            'CELERY_BROKER_URL': 'celery_broker_url', 
            'CELERY_RESULT_BACKEND': 'celery_result_backend',
            'SUPABASE_URL': 'supabase_url',
            'SUPABASE_KEY': 'supabase_key',
            'SUPABASE_SERVICE_KEY': 'supabase_service_key',
            'API_HOST': 'api_host',
            'API_PORT': 'api_port',
            'DEBUG': 'debug',
            'SECRET_KEY': 'secret_key'
        }
        
        # Load from environment variables
        for env_var, field_name in env_mapping.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                kwargs[field_name] = env_value
        
        super().__init__(**kwargs)


# Global settings instance
settings = Settings()