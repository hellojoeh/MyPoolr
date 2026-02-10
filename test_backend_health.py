#!/usr/bin/env python3
"""Test script to check backend health."""

import asyncio
import httpx
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('bot/.env.local')

async def test_backend_health():
    """Test the backend health endpoint."""
    
    backend_url = os.getenv('BACKEND_API_URL', 'https://mypoolr-backend.onrender.com')
    api_key = os.getenv('BACKEND_API_KEY')
    
    print("🏥 Testing Backend Health")
    print("=" * 50)
    print(f"Backend URL: {backend_url}")
    print()
    
    # Test health endpoint
    health_url = f"{backend_url}/health"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            print(f"📤 Checking health: {health_url}")
            
            response = await client.get(health_url)
            
            print(f"📥 Response Status: {response.status_code}")
            print()
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Health Check Response:")
                print(json.dumps(result, indent=2))
            else:
                print("❌ Health Check Failed:")
                try:
                    error_data = response.json()
                    print(json.dumps(error_data, indent=2))
                except:
                    print(response.text)
                    
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        print(f"Error type: {type(e).__name__}")

if __name__ == "__main__":
    asyncio.run(test_backend_health())