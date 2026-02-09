#!/usr/bin/env python3
"""
MyPoolr Telegram Bot Runner
Simple script to start the MyPoolr bot with proper error handling and logging.
"""

import asyncio
import sys
import os
import logging
from pathlib import Path

# Add the bot directory to Python path
bot_dir = Path(__file__).parent
sys.path.insert(0, str(bot_dir))

# Check if we're in a virtual environment
def check_virtual_env():
    """Check if we're running in a virtual environment."""
    in_venv = (
        hasattr(sys, 'real_prefix') or 
        (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    )
    
    if not in_venv:
        venv_path = bot_dir / "venv"
        if venv_path.exists():
            print("⚠️  Virtual environment detected but not activated!")
            print("\n🔧 Please activate the virtual environment first:")
            if os.name == 'nt':
                print("   Windows: activate_env.bat")
                print("   Or manually: venv\\Scripts\\activate.bat")
            else:
                print("   Unix/Linux/Mac: ./activate_env.sh")
                print("   Or manually: source venv/bin/activate")
            print("\nThen run: python run_bot.py")
            return False
        else:
            print("⚠️  No virtual environment found!")
            print("\n🔧 Create one first:")
            print("   python create_env.py")
            return False
    
    return True

try:
    from main import main
    from config import config
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("\nThis usually means:")
    print("1. Dependencies are not installed")
    print("2. Virtual environment is not activated")
    print("3. Configuration files have issues")
    print("\n🔧 Try:")
    print("1. Run: python create_env.py")
    print("2. Activate environment and try again")
    sys.exit(1)


def setup_logging():
    """Setup logging configuration."""
    logging.basicConfig(
        level=getattr(logging, config.log_level.upper(), logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('bot.log', encoding='utf-8')
        ]
    )


def check_environment():
    """Check if all required environment variables are set."""
    required_vars = ['TELEGRAM_BOT_TOKEN']
    missing_vars = []
    
    for var in required_vars:
        if not getattr(config, var.lower(), None):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease check your .env.local file and ensure all required variables are set.")
        return False
    
    return True


def print_startup_info():
    """Print startup information."""
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


async def run_bot():
    """Run the bot with error handling."""
    try:
        await main()
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Bot crashed with error: {e}")
        logging.exception("Bot crashed")
        raise


def main_runner():
    """Main runner function."""
    # Check virtual environment first
    if not check_virtual_env():
        sys.exit(1)
    
    # Setup logging
    setup_logging()
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Print startup info
    print_startup_info()
    
    # Run the bot
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("👋 Goodbye!")
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main_runner()