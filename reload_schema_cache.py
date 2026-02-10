"""
Script to reload PostgREST schema cache in Supabase.

This script provides multiple methods to reload the schema cache:
1. SQL NOTIFY command (recommended)
2. Direct API call to Supabase
3. Instructions for manual dashboard reload

Usage:
    python reload_schema_cache.py
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv('backend/.env.local')

def print_instructions():
    """Print instructions for reloading schema cache."""
    print("=" * 70)
    print("PostgREST Schema Cache Reload Instructions")
    print("=" * 70)
    print()
    
    print("🔴 CRITICAL: Schema cache is out of sync!")
    print("   Error: 'adminname' column not found (should be 'admin_id')")
    print()
    
    print("=" * 70)
    print("METHOD 1: Supabase Dashboard (EASIEST)")
    print("=" * 70)
    print()
    print("1. Go to: https://supabase.com/dashboard")
    print("2. Select your production project")
    print("3. Navigate to: Settings > API")
    print("4. Click: 'Reload schema cache' button")
    print("5. Wait for confirmation message")
    print()
    
    print("=" * 70)
    print("METHOD 2: SQL Editor (RECOMMENDED)")
    print("=" * 70)
    print()
    print("1. Go to: https://supabase.com/dashboard")
    print("2. Select your production project")
    print("3. Navigate to: SQL Editor")
    print("4. Run this command:")
    print()
    print("   NOTIFY pgrst, 'reload schema';")
    print()
    print("5. Execute the query")
    print()
    
    print("=" * 70)
    print("METHOD 3: API Call (ADVANCED)")
    print("=" * 70)
    print()
    
    supabase_url = os.getenv('SUPABASE_URL', 'YOUR_SUPABASE_URL')
    service_key = os.getenv('SUPABASE_SERVICE_KEY', 'YOUR_SERVICE_KEY')
    
    if supabase_url and supabase_url != 'YOUR_SUPABASE_URL':
        print("Using environment variables from backend/.env.local:")
        print(f"   URL: {supabase_url}")
        print()
        print("Run this curl command:")
        print()
        print(f"curl -X POST '{supabase_url}/rest/v1/rpc/reload_schema_cache' \\")
        print(f"  -H 'apikey: {service_key[:20]}...' \\")
        print(f"  -H 'Authorization: Bearer {service_key[:20]}...'")
        print()
    else:
        print("⚠️  Environment variables not found in backend/.env.local")
        print("   Please use Method 1 or Method 2 instead")
        print()
    
    print("=" * 70)
    print("VERIFICATION STEPS")
    print("=" * 70)
    print()
    print("After reloading the cache, test MyPoolr creation:")
    print()
    print("1. Open your Telegram bot")
    print("2. Use /createmypoolr command")
    print("3. Fill in the details")
    print("4. Verify successful creation (no 'adminname' error)")
    print()
    print("Or run: python test_mypoolr_creation.py")
    print()
    
    print("=" * 70)
    print("NEXT STEPS")
    print("=" * 70)
    print()
    print("1. Execute schema cache reload using one of the methods above")
    print("2. Test MyPoolr creation")
    print("3. Update deployment checklist to include cache reload")
    print("4. Document this fix for future reference")
    print()

def main():
    """Main execution function."""
    print_instructions()
    
    print("=" * 70)
    print()
    response = input("Have you reloaded the schema cache? (yes/no): ").strip().lower()
    
    if response == 'yes':
        print()
        print("✅ Great! Now let's verify the fix...")
        print()
        print("Run this command to test:")
        print("   python test_mypoolr_creation.py")
        print()
        print("Or test via Telegram bot directly.")
        print()
    else:
        print()
        print("⚠️  Please reload the schema cache using one of the methods above.")
        print("   This is required to fix the 'adminname' column error.")
        print()

if __name__ == "__main__":
    main()
