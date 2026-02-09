"""Main entry point for MyPoolr Telegram Bot."""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add current directory to path for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from telegram.ext import Application
from loguru import logger

from config import config
from handlers import setup_handlers
from utils.button_manager import ButtonManager
from utils.state_manager import StateManager
from utils.backend_client import BackendClient


async def main():
    """Initialize and start the MyPoolr Telegram Bot."""
    
    # Configure logging
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=getattr(logging, config.log_level.upper())
    )
    
    logger.info("Starting MyPoolr Telegram Bot...")
    logger.info(f"Environment: {config.environment}")
    
    # Create application
    application = Application.builder().token(config.telegram_bot_token).build()
    
    # Initialize backend client
    backend_client = BackendClient()
    
    # Test backend connection
    try:
        health_status = await backend_client.health_check()
        if health_status.get("success", False):
            logger.info("Backend connection verified")
        else:
            logger.warning(f"Backend health check failed: {health_status}")
    except Exception as e:
        logger.error(f"Backend connection test failed: {e}")
        logger.warning("Bot will start but may have limited functionality")
    
    # Initialize managers
    button_manager = ButtonManager()
    state_manager = StateManager()
    
    # Store managers and backend client in application context
    application.bot_data["button_manager"] = button_manager
    application.bot_data["state_manager"] = state_manager
    application.bot_data["backend_client"] = backend_client
    
    # Setup handlers
    setup_handlers(application)
    
    # Start the bot
    try:
        if config.webhook_url:
            logger.info(f"Starting webhook mode: {config.webhook_url}")
            await application.run_webhook(
                listen="0.0.0.0",
                port=8443,
                url_path="webhook",
                webhook_url=f"{config.webhook_url}/webhook"
            )
        else:
            logger.info("Starting polling mode...")
            await application.run_polling(
                allowed_updates=["message", "callback_query"],
                drop_pending_updates=True
            )
    except Exception as e:
        logger.error(f"Error running bot: {e}")
        raise
    finally:
        # Cleanup
        try:
            await backend_client.close()
            await application.shutdown()
        except:
            pass


if __name__ == "__main__":
    asyncio.run(main())