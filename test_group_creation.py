#!/usr/bin/env python3
"""Test script to verify group creation API."""

import asyncio
import httpx
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('bot/.env.local')

async def test_group_creation():
    """Test the group creation API endpoint."""
    
    backend_url = os.getenv('BACKEND_API_URL', 'https://mypoolr-backend.onrender.com')
    api_key = os.getenv('BACKEND_API_KEY')
    
    if not api_key:
        print("❌ BACKEND_API_KEY not found in environment")
        return
    
    # Test data
    test_data = {
        "admin_id": 123456789,
        "name": "Test Group",
        "contribution_amount": 1000.0,
        "rotation_frequency": "monthly",
        "member_limit": 5,
        "country": "KE",
        "tier": "starter",
        "admin_name": "Test User",
        "admin_username": "testuser"
    }
    
    print("🧪 Testing Group Creation API")
    print("=" * 50)
    print(f"Backend URL: {backend_url}")
    print(f"API Key: {api_key[:10]}...")
    print()
    
    # Test the integrated endpoint
    url = f"{backend_url}/integration/mypoolr/create"
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": api_key
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            print(f"📤 Sending request to: {url}")
            print(f"📋 Headers: {headers}")
            print(f"📋 Data: {json.dumps(test_data, indent=2)}")
            print()
            
            response = await client.post(url, json=test_data, headers=headers)
            
            print(f"📥 Response Status: {response.status_code}")
            print(f"📋 Response Headers: {dict(response.headers)}")
            print()
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Success Response:")
                print(json.dumps(result, indent=2))
            else:
                print("❌ Error Response:")
                try:
                    error_data = response.json()
                    print(json.dumps(error_data, indent=2))
                except:
                    print(f"Raw response: {response.text}")
                    
    except httpx.TimeoutException:
        print("❌ Request timed out")
    except httpx.ConnectError as e:
        print(f"❌ Connection error: {e}")
    except Exception as e:
        print(f"❌ Request failed: {e}")
        print(f"Error type: {type(e).__name__}")

if __name__ == "__main__":
    asyncio.run(test_group_creation())