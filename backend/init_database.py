#!/usr/bin/env python3
"""Database initialization script for MyPoolr Circles."""

import asyncio
import logging
from database import db_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def initialize_database():
    """Initialize the database with schema and RLS policies."""
    logger.info("Starting database initialization...")
    
    # Run migrations
    logger.info("Running database migrations...")
    migration_success = db_manager.run_migrations()
    
    if migration_success:
        logger.info("Migrations completed successfully")
    else:
        logger.error("Migrations failed")
        return False
    
    # Verify tables exist
    logger.info("Verifying database tables...")
    tables_exist = await db_manager.create_tables_if_not_exist()
    
    if tables_exist:
        logger.info("Database tables verified successfully")
    else:
        logger.error("Database table verification failed")
        return False
    
    # Health check
    logger.info("Performing database health check...")
    health_ok = await db_manager.health_check()
    
    if health_ok:
        logger.info("Database health check passed")
    else:
        logger.error("Database health check failed")
        return False
    
    logger.info("Database initialization completed successfully!")
    return True


if __name__ == "__main__":
    success = asyncio.run(initialize_database())
    if not success:
        exit(1)