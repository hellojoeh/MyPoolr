"""
Delete Telegram webhook to switch from webhook mode to polling mode.
Run this before deploying to Railway.
"""

import requests
import sys

BOT_TOKEN = "8574272408:AAH7w3cfFwS7AXaSHi9bUmPq_KVPGc3PwQ4"

def delete_webhook():
    """Delete the Telegram webhook."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook"
    
    print("Deleting Telegram webhook...")
    print(f"URL: {url}")
    
    try:
        response = requests.post(url, json={"drop_pending_updates": True})
        result = response.json()
        
        print("\nResponse:")
        print(result)
        
        if result.get("ok"):
            print("\n✅ SUCCESS: Webhook deleted successfully!")
            print("Your bot is now ready for polling mode (Railway deployment)")
            return True
        else:
            print(f"\n❌ ERROR: {result.get('description', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return False

def check_webhook_status():
    """Check current webhook status."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo"
    
    print("\nChecking webhook status...")
    
    try:
        response = requests.get(url)
        result = response.json()
        
        if result.get("ok"):
            webhook_info = result.get("result", {})
            webhook_url = webhook_info.get("url", "")
            
            print("\nCurrent webhook status:")
            print(f"  URL: {webhook_url if webhook_url else '(none - polling mode)'}")
            print(f"  Pending updates: {webhook_info.get('pending_update_count', 0)}")
            
            if webhook_url:
                print(f"\n⚠️  Webhook is currently set to: {webhook_url}")
                print("   You need to delete it to use polling mode on Railway")
            else:
                print("\n✅ No webhook set - ready for polling mode!")
                
    except Exception as e:
        print(f"\n❌ ERROR checking webhook: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("MyPoolr Bot - Webhook Deletion Tool")
    print("=" * 60)
    
    # Check current status
    check_webhook_status()
    
    # Ask for confirmation
    print("\n" + "=" * 60)
    response = input("\nDo you want to delete the webhook? (yes/no): ").strip().lower()
    
    if response in ['yes', 'y']:
        success = delete_webhook()
        
        if success:
            print("\n" + "=" * 60)
            print("Next steps:")
            print("1. Deploy to Railway following RAILWAY_DEPLOYMENT.md")
            print("2. Bot will automatically use polling mode")
            print("3. Test the bot in Telegram")
            print("=" * 60)
        
        sys.exit(0 if success else 1)
    else:
        print("\nCancelled. Webhook not deleted.")
        sys.exit(0)
