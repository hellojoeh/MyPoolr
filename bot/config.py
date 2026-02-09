"""Configuration management for MyPoolr Telegram Bot."""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field
from dotenv import load_dotenv

# Load environment variables from .env.local first, then .env
load_dotenv('.env.local')
load_dotenv('.env')


class BotConfig(BaseSettings):
    """Bot configuration with environment variable support."""
    
    # Telegram Bot Settings
    telegram_bot_token: str = Field(..., env="TELEGRAM_BOT_TOKEN")
    webhook_url: Optional[str] = Field(None, env="WEBHOOK_URL")
    
    # Backend API Settings
    backend_api_url: str = Field("http://localhost:8000", env="BACKEND_API_URL")
    backend_api_key: Optional[str] = Field(None, env="BACKEND_API_KEY")
    
    # Redis Settings
    redis_url: str = Field("redis://localhost:6379/0", env="REDIS_URL")
    
    # Environment Settings
    environment: str = Field("development", env="ENVIRONMENT")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    
    # Bot Settings
    max_buttons_per_row: int = Field(3, env="MAX_BUTTONS_PER_ROW")
    button_callback_timeout: int = Field(300, env="BUTTON_CALLBACK_TIMEOUT")  # 5 minutes
    
    class Config:
        env_file = [".env.local", ".env"]
        env_file_encoding = 'utf-8'
        case_sensitive = False


# Global config instance
config = BotConfig()