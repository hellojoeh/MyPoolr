#!/usr/bin/env python3
"""Set Telegram webhook for Cloudflare Worker bot."""

import requests
import sys

# Configuration
BOT_TOKEN = "8574272408:AAH7w3cfFwS7AXaSHi9bUmPq_KVPGc3PwQ4"
CLOUDFLARE_WORKER_URL = "https://mypoolr-bot.mypoolr.workers.dev"

def set_webhook(webhook_url):
    """Set the Telegram webhook."""
    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
    
    payload = {
        "url": webhook_url,
        "drop_pending_updates": True  # Clear any pending updates
    }
    
    print(f"Setting webhook to: {webhook_url}")
    response = requests.post(api_url, json=payload)
    result = response.json()
    
    if result.get("ok"):
        print("✅ Webhook set successfully!")
        print(f"Response: {result}")
    else:
        print("❌ Failed to set webhook")
        print(f"Error: {result}")
        sys.exit(1)

def get_webhook_info():
    """Get current webhook information."""
    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo"
    
    response = requests.get(api_url)
    result = response.json()
    
    if result.get("ok"):
        info = result.get("result", {})
        print("\n📋 Current Webhook Info:")
        print(f"  URL: {info.get('url', 'Not set')}")
        print(f"  Pending updates: {info.get('pending_update_count', 0)}")
        print(f"  Last error: {info.get('last_error_message', 'None')}")
    else:
        print("❌ Failed to get webhook info")

if __name__ == "__main__":
    print("🤖 Telegram Webhook Setup\n")
    
    # First, show current webhook info
    get_webhook_info()
    
    # Set the new webhook
    print("\n" + "="*50)
    set_webhook(CLOUDFLARE_WORKER_URL)
    
    # Show updated webhook info
    print("\n" + "="*50)
    get_webhook_info()
    
    print("\n✨ Done! Your bot should now respond to messages.")
