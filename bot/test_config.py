#!/usr/bin/env python3
"""Test configuration loading."""

import os
from dotenv import load_dotenv

print("Testing configuration loading...")
print()

# Test environment file loading
print("1. Testing .env.local loading:")
load_dotenv('.env.local')
token = os.getenv('TELEGRAM_BOT_TOKEN')
print(f"   TELEGRAM_BOT_TOKEN: {token[:20]}..." if token else "   TELEGRAM_BOT_TOKEN: Not found")

print()
print("2. Testing pydantic-settings:")
try:
    from config import config
    print(f"   Bot token loaded: {config.telegram_bot_token[:20]}...")
    print(f"   Environment: {config.environment}")
    print(f"   Log level: {config.log_level}")
    print("   ✅ Configuration loaded successfully!")
except Exception as e:
    print(f"   ❌ Configuration failed: {e}")

print()
print("3. Testing imports:")
try:
    from telegram.ext import Application
    print("   ✅ telegram imported")
except ImportError as e:
    print(f"   ❌ telegram import failed: {e}")

try:
    from handlers import setup_handlers
    print("   ✅ handlers imported")
except ImportError as e:
    print(f"   ❌ handlers import failed: {e}")

try:
    from utils.button_manager import ButtonManager
    print("   ✅ button_manager imported")
except ImportError as e:
    print(f"   ❌ button_manager import failed: {e}")

print()
print("Test completed!")