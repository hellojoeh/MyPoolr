"""
Test script to verify MyPoolr creation after schema cache reload.

This script tests the mypoolr creation endpoint to ensure the
schema cache issue has been resolved.

Usage:
    python test_mypoolr_creation.py
"""

import os
import sys
import requests
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv('backend/.env.local')

def test_mypoolr_creation():
    """Test MyPoolr creation via API."""
    
    # Get backend URL from environment
    backend_url = os.getenv('BACKEND_URL')
    
    if not backend_url:
        print("❌ Error: BACKEND_URL not found in backend/.env.local")
        print("   Please set BACKEND_URL in your environment file")
        return False
    
    print("=" * 70)
    print("Testing MyPoolr Creation")
    print("=" * 70)
    print()
    print(f"Backend URL: {backend_url}")
    print()
    
    # Test data
    test_data = {
        "name": f"Schema Cache Test {datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "admin_id": 123456789,
        "contribution_amount": 1000.0,
        "rotation_frequency": "monthly",
        "member_limit": 10,
        "tier": "starter"
    }
    
    print("Test Data:")
    for key, value in test_data.items():
        print(f"  {key}: {value}")
    print()
    
    print("Sending request...")
    print()
    
    try:
        # Make API request
        response = requests.post(
            f"{backend_url}/mypoolr/create",
            json=test_data,
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        print()
        
        # Parse response
        try:
            response_data = response.json()
            print("Response:")
            print(response_data)
            print()
        except:
            print("Response (raw):")
            print(response.text)
            print()
        
        # Check for success
        if response.status_code == 200:
            print("✅ SUCCESS: MyPoolr created successfully!")
            print()
            print("Schema cache issue is RESOLVED! ✨")
            print()
            
            if 'id' in response_data:
                print(f"Created MyPoolr ID: {response_data['id']}")
                print()
            
            return True
        
        elif response.status_code == 400:
            print("⚠️  Bad Request (400)")
            print()
            
            if 'adminname' in str(response_data).lower():
                print("❌ SCHEMA CACHE ISSUE STILL EXISTS!")
                print("   The 'adminname' column error is still present.")
                print()
                print("Action Required:")
                print("1. Verify schema cache reload was executed")
                print("2. Try reloading again using: python reload_schema_cache.py")
                print("3. Wait 1-2 minutes for cache to refresh")
                print()
                return False
            else:
                print("Validation error (not schema cache related):")
                print(response_data)
                print()
                return False
        
        else:
            print(f"❌ Error: Unexpected status code {response.status_code}")
            print()
            return False
    
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Cannot reach backend")
        print(f"   URL: {backend_url}")
        print()
        print("Possible causes:")
        print("1. Backend is not running")
        print("2. Incorrect BACKEND_URL in .env.local")
        print("3. Network connectivity issue")
        print()
        return False
    
    except requests.exceptions.Timeout:
        print("❌ Timeout Error: Request took too long")
        print()
        return False
    
    except Exception as e:
        print(f"❌ Unexpected Error: {str(e)}")
        print()
        return False

def main():
    """Main execution function."""
    print()
    success = test_mypoolr_creation()
    print()
    
    if success:
        print("=" * 70)
        print("NEXT STEPS")
        print("=" * 70)
        print()
        print("1. ✅ Schema cache issue resolved")
        print("2. Test via Telegram bot to confirm end-to-end")
        print("3. Update deployment documentation")
        print("4. Add schema cache reload to deployment checklist")
        print()
    else:
        print("=" * 70)
        print("TROUBLESHOOTING")
        print("=" * 70)
        print()
        print("If the issue persists:")
        print()
        print("1. Verify you reloaded the schema cache")
        print("2. Wait 1-2 minutes for cache to propagate")
        print("3. Check Supabase dashboard for any errors")
        print("4. Verify migrations were applied correctly")
        print("5. Contact Supabase support if issue continues")
        print()
        print("Run: python reload_schema_cache.py for instructions")
        print()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
