#!/usr/bin/env python3
"""Script to add country column to mypoolr table in production database."""

import asyncio
import logging
import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from database import db_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def add_country_column():
    """Add country column to mypoolr table."""
    logger.info("Adding country column to mypoolr table...")
    
    try:
        # First, check if the column already exists
        logger.info("Checking if country column already exists...")
        
        # Try to select country column - if it fails, column doesn't exist
        try:
            result = db_manager.service_client.table("mypoolr").select("country").limit(1).execute()
            logger.info("Country column already exists!")
            return True
        except Exception:
            logger.info("Country column does not exist, adding it...")
        
        # Add the country column using SQL
        # Note: Supabase/PostgREST doesn't support DDL directly, so we need to use the SQL editor
        # or add it through the Supabase dashboard
        
        logger.info("⚠️  MANUAL ACTION REQUIRED:")
        logger.info("Please run the following SQL in your Supabase SQL editor:")
        logger.info("")
        logger.info("-- Add country column to mypoolr table")
        logger.info("ALTER TABLE mypoolr ADD COLUMN country VARCHAR(2) DEFAULT 'KE' CHECK (length(country) = 2);")
        logger.info("")
        logger.info("-- Create index for country-based queries")
        logger.info("CREATE INDEX IF NOT EXISTS idx_mypoolr_country ON mypoolr(country);")
        logger.info("")
        logger.info("-- Update existing records to have default country")
        logger.info("UPDATE mypoolr SET country = 'KE' WHERE country IS NULL;")
        logger.info("")
        logger.info("-- Make country NOT NULL after setting defaults")
        logger.info("ALTER TABLE mypoolr ALTER COLUMN country SET NOT NULL;")
        logger.info("")
        
        return False
        
    except Exception as e:
        logger.error(f"Error checking/adding country column: {e}")
        return False


async def verify_country_column():
    """Verify that the country column exists and works."""
    logger.info("Verifying country column...")
    
    try:
        # Try to select from the country column
        result = db_manager.service_client.table("mypoolr").select("id, name, country").limit(5).execute()
        
        if result.data:
            logger.info("✅ Country column exists and is accessible!")
            logger.info(f"Sample data: {result.data}")
            return True
        else:
            logger.info("✅ Country column exists but no data found")
            return True
            
    except Exception as e:
        logger.error(f"❌ Country column verification failed: {e}")
        return False


if __name__ == "__main__":
    print("🔧 MyPoolr Database Migration - Add Country Column")
    print("=" * 60)
    
    # First try to add the column
    success = asyncio.run(add_country_column())
    
    if not success:
        print("\n⚠️  Please run the SQL commands shown above in your Supabase dashboard")
        print("Then run this script again with --verify to test the column")
        exit(1)
    
    # If column exists, verify it works
    verified = asyncio.run(verify_country_column())
    
    if verified:
        print("\n✅ Country column is ready!")
        print("You can now test group creation with country support.")
    else:
        print("\n❌ Country column verification failed")
        exit(1)