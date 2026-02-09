#!/usr/bin/env python3
"""
Simple MyPoolr Bot Runner - Alternative version to avoid event loop issues
"""

import logging
import sys
from pathlib import Path

# Add the bot directory to Python path
bot_dir = Path(__file__).parent
sys.path.insert(0, str(bot_dir))

from telegram.ext import Application
from config import config
from handlers import setup_handlers
from utils.button_manager import ButtonManager
from utils.state_manager import StateManager


def main():
    """Initialize and start the MyPoolr Telegram Bot."""
    
    # Configure logging
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=getattr(logging, config.log_level.upper())
    )
    
    print("🚀 MyPoolr Telegram Bot")
    print("=" * 50)
    print(f"Environment: {config.environment}")
    print(f"Log Level: {config.log_level}")
    print(f"Backend API: {config.backend_api_url}")
    print(f"Redis URL: {config.redis_url}")
    
    if config.webhook_url:
        print(f"Mode: Webhook ({config.webhook_url})")
    else:
        print("Mode: Polling")
    
    print("=" * 50)
    print("Bot is starting...")
    print("Press Ctrl+C to stop the bot")
    print()
    
    # Create application
    application = Application.builder().token(config.telegram_bot_token).build()
    
    # Initialize managers
    button_manager = ButtonManager()
    state_manager = StateManager()
    
    # Store managers in application context
    application.bot_data["button_manager"] = button_manager
    application.bot_data["state_manager"] = state_manager
    
    # Setup handlers
    setup_handlers(application)
    
    # Start the bot
    try:
        if config.webhook_url:
            print(f"Starting webhook mode: {config.webhook_url}")
            application.run_webhook(
                listen="0.0.0.0",
                port=8443,
                url_path="webhook",
                webhook_url=f"{config.webhook_url}/webhook"
            )
        else:
            print("Starting polling mode...")
            application.run_polling(
                allowed_updates=["message", "callback_query"],
                drop_pending_updates=True
            )
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Bot crashed with error: {e}")
        logging.exception("Bot crashed")
        raise


if __name__ == "__main__":
    main()