#!/usr/bin/env python3
"""Test API authentication setup."""

import sys
import os
from dotenv import load_dotenv

def test_api_auth():
    """Test API authentication configuration."""
    
    print("🔐 Testing API Authentication Setup")
    print("=" * 50)
    
    # Load backend environment
    load_dotenv('backend/.env.local')
    backend_api_key = os.getenv('BACKEND_API_KEY')
    secret_key = os.getenv('SECRET_KEY')
    webhook_secret = os.getenv('WEBHOOK_SECRET_TOKEN')
    
    # Load bot environment
    load_dotenv('bot/.env.local')
    bot_api_key = os.getenv('BACKEND_API_KEY')
    bot_webhook_secret = os.getenv('WEBHOOK_SECRET_TOKEN')
    backend_url = os.getenv('BACKEND_API_URL')
    
    print("📋 Backend Configuration:")
    print(f"   API Key: {backend_api_key[:10] if backend_api_key else 'Not set'}...{backend_api_key[-10:] if backend_api_key else ''}")
    print(f"   Secret Key: {secret_key[:10] if secret_key else 'Not set'}...{secret_key[-10:] if secret_key else ''}")
    print(f"   Webhook Secret: {webhook_secret[:8] if webhook_secret else 'Not set'}...{webhook_secret[-8:] if webhook_secret else ''}")
    
    print("\n📋 Bot Configuration:")
    print(f"   API Key: {bot_api_key[:10] if bot_api_key else 'Not set'}...{bot_api_key[-10:] if bot_api_key else ''}")
    print(f"   Webhook Secret: {bot_webhook_secret[:8] if bot_webhook_secret else 'Not set'}...{bot_webhook_secret[-8:] if bot_webhook_secret else ''}")
    print(f"   Backend URL: {backend_url}")
    
    # Validation
    issues = []
    
    if not backend_api_key:
        issues.append("Backend API key not set")
    
    if not secret_key:
        issues.append("Backend secret key not set")
    
    if not webhook_secret:
        issues.append("Webhook secret token not set")
    
    if not bot_api_key:
        issues.append("Bot API key not set")
    
    if backend_api_key != bot_api_key:
        issues.append("API keys don't match between backend and bot")
    
    if webhook_secret != bot_webhook_secret:
        issues.append("Webhook secrets don't match between backend and bot")
    
    if backend_url == "http://localhost:8000":
        issues.append("Backend URL still set to localhost (update for production)")
    
    if issues:
        print("\n❌ Issues Found:")
        for issue in issues:
            print(f"   • {issue}")
        return False
    else:
        print("\n✅ All authentication configuration looks good!")
        
        print("\n📋 Next Steps:")
        print("1. Deploy backend to get production URL")
        print("2. Update BACKEND_API_URL and WEBHOOK_URL in bot/.env.local")
        print("3. Set Telegram webhook with: python setup_webhook.py")
        print("4. Test the complete system")
        
        return True

if __name__ == "__main__":
    success = test_api_auth()
    sys.exit(0 if success else 1)