"""Database connection and configuration for Supabase."""

import os
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path
from supabase import create_client, Client
from config import settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages Supabase database connections and migrations."""
    
    def __init__(self):
        self._client: Optional[Client] = None
        self._service_client: Optional[Client] = None
        self.migrations_dir = Path(__file__).parent / "migrations"
    
    @property
    def client(self) -> Client:
        """Get the standard Supabase client."""
        if self._client is None:
            self._client = create_client(
                settings.supabase_url,
                settings.supabase_key
            )
        return self._client
    
    @property
    def service_client(self) -> Client:
        """Get the service role Supabase client for admin operations."""
        if self._service_client is None:
            self._service_client = create_client(
                settings.supabase_url,
                settings.supabase_service_key
            )
        return self._service_client
    
    async def health_check(self) -> bool:
        """Check if database connection is healthy."""
        try:
            # Test connection with a simple query
            result = self.service_client.table("mypoolr").select("id").limit(1).execute()
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    def run_migrations(self) -> bool:
        """Run database migrations from the migrations directory."""
        try:
            if not self.migrations_dir.exists():
                logger.warning("Migrations directory not found")
                return True
            
            # Get list of migration files
            migration_files = sorted([
                f for f in self.migrations_dir.glob("*.sql")
                if f.is_file()
            ])
            
            if not migration_files:
                logger.info("No migration files found")
                return True
            
            # Execute each migration
            for migration_file in migration_files:
                logger.info(f"Running migration: {migration_file.name}")
                
                with open(migration_file, 'r') as f:
                    sql_content = f.read()
                
                # Execute the SQL using Supabase RPC
                # Note: This is a simplified approach. In production, you'd want
                # proper migration tracking and rollback capabilities
                try:
                    self.service_client.rpc('exec_sql', {'sql': sql_content}).execute()
                    logger.info(f"Migration {migration_file.name} completed successfully")
                except Exception as e:
                    logger.error(f"Migration {migration_file.name} failed: {e}")
                    # For now, we'll continue with other migrations
                    # In production, you might want to stop here
                    continue
            
            return True
            
        except Exception as e:
            logger.error(f"Migration process failed: {e}")
            return False
    
    async def create_tables_if_not_exist(self) -> bool:
        """Ensure core tables exist (fallback if migrations fail)."""
        try:
            # This is a simplified check - just verify main tables exist
            tables_to_check = ['mypoolr', 'member', 'transaction']
            
            for table in tables_to_check:
                try:
                    result = self.service_client.table(table).select("*").limit(1).execute()
                    logger.info(f"Table {table} exists and is accessible")
                except Exception as e:
                    logger.warning(f"Table {table} may not exist or is not accessible: {e}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Table verification failed: {e}")
            return False
    
    def get_mypoolr_by_id(self, mypoolr_id: str) -> Optional[Dict[str, Any]]:
        """Get MyPoolr by ID using service client."""
        try:
            result = self.service_client.table("mypoolr").select("*").eq("id", mypoolr_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to get MyPoolr {mypoolr_id}: {e}")
            return None
    
    def get_members_by_mypoolr(self, mypoolr_id: str) -> List[Dict[str, Any]]:
        """Get all members for a MyPoolr group."""
        try:
            result = self.service_client.table("member").select("*").eq("mypoolr_id", mypoolr_id).execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Failed to get members for MyPoolr {mypoolr_id}: {e}")
            return []
    
    def get_transactions_by_mypoolr(self, mypoolr_id: str) -> List[Dict[str, Any]]:
        """Get all transactions for a MyPoolr group."""
        try:
            result = self.service_client.table("transaction").select("*").eq("mypoolr_id", mypoolr_id).execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Failed to get transactions for MyPoolr {mypoolr_id}: {e}")
            return []


# Global database manager instance
db_manager = DatabaseManager()