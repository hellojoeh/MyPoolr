#!/usr/bin/env python3
"""Test database schema and provide migration instructions."""

import asyncio
import logging
import sys
import os
import json

# Add backend directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from database import db_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_database_schema():
    """Test the current database schema."""
    logger.info("Testing database schema...")
    
    try:
        # Test basic mypoolr table access
        logger.info("Testing mypoolr table access...")
        result = db_manager.service_client.table("mypoolr").select("*").limit(1).execute()
        
        if result.data:
            logger.info("✅ mypoolr table accessible")
            sample_record = result.data[0]
            logger.info(f"Sample record fields: {list(sample_record.keys())}")
            
            # Check if country field exists
            if 'country' in sample_record:
                logger.info("✅ Country column exists!")
                return True
            else:
                logger.info("❌ Country column missing")
                return False
        else:
            logger.info("✅ mypoolr table accessible but empty")
            
            # Try to insert a test record to see what fields are required
            logger.info("Testing required fields by attempting insert...")
            
            test_data = {
                "name": "Test Group",
                "admin_id": 123456789,
                "contribution_amount": 1000.0,
                "rotation_frequency": "monthly",
                "member_limit": 5,
                "tier": "starter",
                "country": "KE"
            }
            
            try:
                insert_result = db_manager.service_client.table("mypoolr").insert(test_data).execute()
                logger.info("✅ Test insert successful - country column exists!")
                
                # Clean up test record
                if insert_result.data:
                    test_id = insert_result.data[0]['id']
                    db_manager.service_client.table("mypoolr").delete().eq("id", test_id).execute()
                    logger.info("🧹 Test record cleaned up")
                
                return True
                
            except Exception as insert_error:
                logger.error(f"❌ Test insert failed: {insert_error}")
                
                if "country" in str(insert_error).lower():
                    logger.info("Country column is missing from database schema")
                    return False
                else:
                    logger.info("Insert failed for other reasons")
                    return False
            
    except Exception as e:
        logger.error(f"Database schema test failed: {e}")
        return False


def print_migration_instructions():
    """Print instructions for adding the country column."""
    print("\n" + "="*60)
    print("🔧 DATABASE MIGRATION REQUIRED")
    print("="*60)
    print("\nThe 'country' column is missing from the mypoolr table.")
    print("Please run the following SQL commands in your Supabase SQL editor:")
    print("\n-- Step 1: Add country column")
    print("ALTER TABLE mypoolr ADD COLUMN country VARCHAR(2) DEFAULT 'KE' CHECK (length(country) = 2);")
    print("\n-- Step 2: Create index")
    print("CREATE INDEX IF NOT EXISTS idx_mypoolr_country ON mypoolr(country);")
    print("\n-- Step 3: Update existing records (if any)")
    print("UPDATE mypoolr SET country = 'KE' WHERE country IS NULL;")
    print("\n-- Step 4: Make column required")
    print("ALTER TABLE mypoolr ALTER COLUMN country SET NOT NULL;")
    print("\n" + "="*60)
    print("After running these commands, test group creation again.")
    print("="*60)


if __name__ == "__main__":
    print("🔍 Testing Database Schema for Country Support")
    print("=" * 60)
    
    schema_ok = asyncio.run(test_database_schema())
    
    if schema_ok:
        print("\n✅ Database schema is ready for country support!")
        print("You can now test group creation.")
    else:
        print_migration_instructions()