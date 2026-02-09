#!/usr/bin/env python3
"""Test configuration loading."""

import sys
import os
from dotenv import load_dotenv

# Add backend to path
sys.path.insert(0, 'backend')

def test_config():
    """Test if configuration is loading correctly."""
    
    print("🔍 Testing Configuration Loading...")
    
    # Load environment file manually
    load_dotenv('backend/.env.local')
    
    print("📋 Environment Variables:")
    redis_url = os.getenv('REDIS_URL')
    celery_broker = os.getenv('CELERY_BROKER_URL')
    celery_result = os.getenv('CELERY_RESULT_BACKEND')
    
    print(f"   REDIS_URL: {redis_url[:30] if redis_url else 'Not found'}...")
    print(f"   CELERY_BROKER_URL: {celery_broker[:30] if celery_broker else 'Not found'}...")
    print(f"   CELERY_RESULT_BACKEND: {celery_result[:30] if celery_result else 'Not found'}...")
    
    try:
        from config import settings
        
        print(f"\n✅ Config loaded successfully")
        print(f"📍 Redis URL: {settings.redis_url[:30]}...")
        print(f"📍 Celery Broker: {settings.celery_broker_url[:30]}...")
        print(f"📍 Celery Result Backend: {settings.celery_result_backend[:30]}...")
        
        # Check if Redis Cloud URL is loaded
        if "localhost" in settings.redis_url:
            print("❌ Still using localhost Redis - environment not loaded correctly")
            return False
        else:
            print("✅ Redis Cloud URL loaded correctly")
            return True
            
    except Exception as e:
        print(f"❌ Config loading failed: {e}")
        return False

if __name__ == "__main__":
    success = test_config()
    sys.exit(0 if success else 1)