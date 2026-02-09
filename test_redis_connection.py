#!/usr/bin/env python3
"""
Test Redis Cloud connection for MyPoolr Circles.
Run this script to verify your Redis Cloud setup is working.
"""

import os
import sys
from dotenv import load_dotenv

def test_redis_connection():
    """Test Redis connection using environment variables."""
    
    # Load environment variables
    load_dotenv('backend/.env.local')
    
    redis_url = os.getenv('REDIS_URL')
    
    if not redis_url:
        print("❌ REDIS_URL not found in environment variables")
        return False
    
    print(f"🔍 Testing Redis connection...")
    print(f"📍 Redis URL: {redis_url[:20]}...{redis_url[-10:] if len(redis_url) > 30 else redis_url}")
    
    try:
        import redis
        
        # Parse Redis URL
        r = redis.from_url(redis_url)
        
        # Test basic operations
        print("\n🧪 Running Redis tests...")
        
        # Test 1: Ping
        print("1. Testing ping...")
        response = r.ping()
        if response:
            print("   ✅ Ping successful")
        else:
            print("   ❌ Ping failed")
            return False
        
        # Test 2: Set and Get
        print("2. Testing set/get...")
        test_key = "mypoolr:test:connection"
        test_value = "Hello from MyPoolr!"
        
        r.set(test_key, test_value, ex=60)  # Expires in 60 seconds
        retrieved_value = r.get(test_key)
        
        if retrieved_value and retrieved_value.decode() == test_value:
            print("   ✅ Set/Get successful")
        else:
            print("   ❌ Set/Get failed")
            return False
        
        # Test 3: List operations (for Celery queues)
        print("3. Testing list operations (Celery queues)...")
        queue_name = "mypoolr:test:queue"
        
        r.lpush(queue_name, "test_task_1", "test_task_2")
        queue_length = r.llen(queue_name)
        
        if queue_length >= 2:
            print("   ✅ List operations successful")
        else:
            print("   ❌ List operations failed")
            return False
        
        # Test 4: Hash operations (for session storage)
        print("4. Testing hash operations (session storage)...")
        session_key = "mypoolr:test:session:12345"
        
        r.hset(session_key, mapping={
            "user_id": "12345",
            "state": "creating_mypoolr",
            "step": "1"
        })
        r.expire(session_key, 3600)  # Expires in 1 hour
        
        session_data = r.hgetall(session_key)
        
        if session_data and b'user_id' in session_data:
            print("   ✅ Hash operations successful")
        else:
            print("   ❌ Hash operations failed")
            return False
        
        # Cleanup test data
        print("\n🧹 Cleaning up test data...")
        r.delete(test_key, queue_name, session_key)
        
        # Test 5: Get Redis info
        print("5. Getting Redis server info...")
        info = r.info()
        
        print(f"   📊 Redis version: {info.get('redis_version', 'Unknown')}")
        print(f"   💾 Used memory: {info.get('used_memory_human', 'Unknown')}")
        print(f"   🔗 Connected clients: {info.get('connected_clients', 'Unknown')}")
        
        print("\n🎉 All Redis tests passed!")
        print("✅ Your Redis Cloud connection is working perfectly!")
        
        return True
        
    except ImportError:
        print("❌ Redis package not installed. Run: pip install redis")
        return False
    except redis.ConnectionError as e:
        print(f"❌ Redis connection failed: {e}")
        print("\n🔧 Troubleshooting tips:")
        print("1. Check your Redis Cloud connection string")
        print("2. Verify your Redis Cloud database is running")
        print("3. Check if your IP is whitelisted in Redis Cloud")
        print("4. Ensure the password is correct")
        return False
    except redis.AuthenticationError as e:
        print(f"❌ Redis authentication failed: {e}")
        print("\n🔧 Check your Redis Cloud username and password")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_celery_connection():
    """Test Celery connection to Redis."""
    
    print("\n🔍 Testing Celery connection...")
    
    try:
        # Add backend to path
        sys.path.insert(0, 'backend')
        
        from celery_app import celery_app
        
        # Test Celery broker connection
        inspect = celery_app.control.inspect()
        
        # This will fail if broker is not accessible
        stats = inspect.stats()
        
        if stats is None:
            print("⚠️  No Celery workers running (this is normal for testing)")
            print("✅ Celery broker connection successful")
        else:
            print("✅ Celery connection successful with active workers")
            
        return True
        
    except Exception as e:
        print(f"❌ Celery connection failed: {e}")
        print("💡 This might be normal if Celery worker is not running")
        return False

if __name__ == "__main__":
    print("🚀 MyPoolr Circles - Redis Cloud Connection Test")
    print("=" * 50)
    
    # Test Redis connection
    redis_success = test_redis_connection()
    
    # Test Celery connection
    celery_success = test_celery_connection()
    
    print("\n" + "=" * 50)
    if redis_success:
        print("🎉 Redis Cloud setup is complete and working!")
        print("\n📋 Next steps:")
        print("1. Update your .env.local files with the actual Redis Cloud URL")
        print("2. Start your backend: cd backend && python main.py")
        print("3. Start Celery worker: cd backend && celery -A celery_app worker --loglevel=info")
        print("4. Your Redis will automatically handle:")
        print("   • Background task queues")
        print("   • Bot conversation states")
        print("   • Caching for performance")
        print("   • Session management")
    else:
        print("❌ Redis Cloud setup needs attention")
        print("Please check your connection string and try again")
    
    sys.exit(0 if redis_success else 1)