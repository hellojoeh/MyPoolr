#!/usr/bin/env python3
"""Setup Telegram webhook for MyPoolr Circles production."""

import requests
import json
import sys
from dotenv import load_dotenv
import os

def setup_webhook(bot_token, webhook_url, secret_token=None):
    """Set up Telegram webhook."""
    
    print(f"🔗 Setting up webhook...")
    print(f"📍 Bot Token: {bot_token[:10]}...{bot_token[-10:]}")
    print(f"📍 Webhook URL: {webhook_url}")
    
    # Prepare webhook data
    webhook_data = {
        "url": webhook_url,
        "max_connections": 40,
        "allowed_updates": [
            "message",
            "callback_query", 
            "inline_query",
            "chosen_inline_result"
        ]
    }
    
    if secret_token:
        webhook_data["secret_token"] = secret_token
        print(f"🔐 Secret Token: {secret_token[:8]}...{secret_token[-8:]}")
    
    # Set webhook
    api_url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
    
    try:
        response = requests.post(api_url, json=webhook_data, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        if result.get("ok"):
            print("✅ Webhook set successfully!")
            print(f"📋 Response: {result.get('description', 'Success')}")
            return True
        else:
            print(f"❌ Failed to set webhook: {result.get('description', 'Unknown error')}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def get_webhook_info(bot_token):
    """Get current webhook information."""
    
    print("🔍 Getting current webhook info...")
    
    api_url = f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"
    
    try:
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        if result.get("ok"):
            webhook_info = result.get("result", {})
            
            print("📋 Current Webhook Info:")
            print(f"   URL: {webhook_info.get('url', 'Not set')}")
            print(f"   Has Custom Certificate: {webhook_info.get('has_custom_certificate', False)}")
            print(f"   Pending Updates: {webhook_info.get('pending_update_count', 0)}")
            print(f"   Max Connections: {webhook_info.get('max_connections', 'Not set')}")
            print(f"   Allowed Updates: {webhook_info.get('allowed_updates', 'All')}")
            
            if webhook_info.get('last_error_date'):
                print(f"   Last Error: {webhook_info.get('last_error_message', 'Unknown')}")
                print(f"   Last Error Date: {webhook_info.get('last_error_date')}")
            
            return webhook_info
        else:
            print(f"❌ Failed to get webhook info: {result.get('description', 'Unknown error')}")
            return None
            
    except Exception as e:
        print(f"❌ Error getting webhook info: {e}")
        return None

def delete_webhook(bot_token):
    """Delete current webhook."""
    
    print("🗑️ Deleting current webhook...")
    
    api_url = f"https://api.telegram.org/bot{bot_token}/deleteWebhook"
    
    try:
        response = requests.post(api_url, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        if result.get("ok"):
            print("✅ Webhook deleted successfully!")
            return True
        else:
            print(f"❌ Failed to delete webhook: {result.get('description', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Error deleting webhook: {e}")
        return False

def main():
    """Main webhook setup function."""
    
    print("🚀 MyPoolr Circles - Webhook Setup")
    print("=" * 50)
    
    # Load environment variables
    load_dotenv('bot/.env.local')
    
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    webhook_url = os.getenv('WEBHOOK_URL')
    secret_token = os.getenv('WEBHOOK_SECRET_TOKEN')
    
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN not found in environment")
        return False
    
    if not webhook_url or webhook_url == "https://your-domain.com/webhook":
        print("❌ WEBHOOK_URL not configured properly")
        print("💡 Please update WEBHOOK_URL in bot/.env.local with your production URL")
        return False
    
    # Show current webhook info
    get_webhook_info(bot_token)
    
    print("\n" + "=" * 50)
    
    # Ask user what to do
    print("What would you like to do?")
    print("1. Set new webhook")
    print("2. Get webhook info only")
    print("3. Delete current webhook")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        success = setup_webhook(bot_token, webhook_url, secret_token)
        if success:
            print("\n🎉 Webhook setup complete!")
            print("📋 Next steps:")
            print("1. Deploy your backend to production")
            print("2. Update WEBHOOK_URL with your production backend URL")
            print("3. Test the webhook by sending a message to your bot")
        return success
        
    elif choice == "2":
        get_webhook_info(bot_token)
        return True
        
    elif choice == "3":
        success = delete_webhook(bot_token)
        return success
        
    else:
        print("❌ Invalid choice")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)