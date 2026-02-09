"""Concurrent operation safety manager for MyPoolr system."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable, TypeVar, Generic
from uuid import UUID, uuid4
from contextlib import asynccontextmanager
from enum import Enum
import json
import hashlib

from ..database import DatabaseManager
from ..models.mypoolr import MyPoolr
from ..models.member import Member
from ..models.transaction import Transaction


logger = logging.getLogger(__name__)
T = TypeVar('T')


class LockType(str, Enum):
    """Types of locks for different operations."""
    MYPOOLR_WRITE = "mypoolr_write"
    MEMBER_WRITE = "member_write"
    TRANSACTION_WRITE = "transaction_write"
    ROTATION_ADVANCE = "rotation_advance"
    SECURITY_DEPOSIT = "security_deposit"
    DEFAULT_HANDLING = "default_handling"
    TIER_UPGRADE = "tier_upgrade"


class LockScope(str, Enum):
    """Scope of locks."""
    GLOBAL = "global"
    MYPOOLR = "mypoolr"
    MEMBER = "member"
    TRANSACTION = "transaction"


class OperationLock:
    """Represents a distributed lock for concurrent operations."""
    
    def __init__(
        self, 
        lock_id: str,
        lock_type: LockType,
        scope: LockScope,
        resource_id: str,
        holder_id: str,
        expires_at: datetime,
        metadata: Dict[str, Any] = None
    ):
        self.lock_id = lock_id
        self.lock_type = lock_type
        self.scope = scope
        self.resource_id = resource_id
        self.holder_id = holder_id
        self.expires_at = expires_at
        self.metadata = metadata or {}
        self.created_at = datetime.utcnow()


class ConcurrencyManager:
    """Manages concurrent operations and distributed locking."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.local_locks: Dict[str, asyncio.Lock] = {}
        self.lock_timeout = timedelta(minutes=5)  # Default lock timeout
        self.cleanup_interval = timedelta(minutes=1)
        self._cleanup_task: Optional[asyncio.Task] = None
        self._start_cleanup_task()
    
    def _start_cleanup_task(self):
        """Start background task to clean up expired locks."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_expired_locks())
    
    async def _cleanup_expired_locks(self):
        """Background task to clean up expired locks."""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval.total_seconds())
                await self._remove_expired_locks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in lock cleanup task: {e}")
    
    async def _remove_expired_locks(self):
        """Remove expired locks from database."""
        try:
            current_time = datetime.utcnow()
            
            result = self.db.service_client.table("operation_locks").delete().lt(
                "expires_at", current_time.isoformat()
            ).execute()
            
            if result.data:
                logger.info(f"Cleaned up {len(result.data)} expired locks")
                
        except Exception as e:
            logger.error(f"Failed to cleanup expired locks: {e}")
    
    def _generate_lock_key(self, lock_type: LockType, resource_id: str) -> str:
        """Generate a unique lock key."""
        return f"{lock_type.value}:{resource_id}"
    
    def _generate_holder_id(self) -> str:
        """Generate a unique holder ID for this process."""
        import os
        import socket
        
        process_id = os.getpid()
        hostname = socket.gethostname()
        timestamp = datetime.utcnow().timestamp()
        
        return hashlib.md5(f"{hostname}:{process_id}:{timestamp}".encode()).hexdigest()[:16]
    
    @asynccontextmanager
    async def acquire_lock(
        self,
        lock_type: LockType,
        resource_id: str,
        scope: LockScope = LockScope.MYPOOLR,
        timeout: Optional[timedelta] = None,
        metadata: Dict[str, Any] = None
    ):
        """Acquire a distributed lock for an operation."""
        
        lock_key = self._generate_lock_key(lock_type, resource_id)
        holder_id = self._generate_holder_id()
        lock_timeout = timeout or self.lock_timeout
        expires_at = datetime.utcnow() + lock_timeout
        
        # First acquire local lock to prevent race conditions within this process
        if lock_key not in self.local_locks:
            self.local_locks[lock_key] = asyncio.Lock()
        
        local_lock = self.local_locks[lock_key]
        
        async with local_lock:
            # Try to acquire distributed lock
            lock = await self._acquire_distributed_lock(
                lock_type, resource_id, scope, holder_id, expires_at, metadata
            )
            
            if lock is None:
                raise ConcurrencyError(f"Failed to acquire lock for {lock_type.value}:{resource_id}")
            
            try:
                yield lock
            finally:
                await self._release_distributed_lock(lock)
    
    async def _acquire_distributed_lock(
        self,
        lock_type: LockType,
        resource_id: str,
        scope: LockScope,
        holder_id: str,
        expires_at: datetime,
        metadata: Dict[str, Any] = None
    ) -> Optional[OperationLock]:
        """Acquire distributed lock in database."""
        
        lock_id = str(uuid4())
        
        try:
            # Check if lock already exists and is not expired
            existing_result = self.db.service_client.table("operation_locks").select("*").eq(
                "lock_type", lock_type.value
            ).eq("resource_id", resource_id).gt(
                "expires_at", datetime.utcnow().isoformat()
            ).execute()
            
            if existing_result.data:
                logger.warning(f"Lock already exists for {lock_type.value}:{resource_id}")
                return None
            
            # Try to insert new lock
            lock_data = {
                "id": lock_id,
                "lock_type": lock_type.value,
                "scope": scope.value,
                "resource_id": resource_id,
                "holder_id": holder_id,
                "expires_at": expires_at.isoformat(),
                "metadata": json.dumps(metadata or {}),
                "created_at": datetime.utcnow().isoformat()
            }
            
            result = self.db.service_client.table("operation_locks").insert(lock_data).execute()
            
            if result.data:
                logger.info(f"Acquired lock {lock_id} for {lock_type.value}:{resource_id}")
                return OperationLock(
                    lock_id=lock_id,
                    lock_type=lock_type,
                    scope=scope,
                    resource_id=resource_id,
                    holder_id=holder_id,
                    expires_at=expires_at,
                    metadata=metadata
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to acquire distributed lock: {e}")
            return None
    
    async def _release_distributed_lock(self, lock: OperationLock):
        """Release distributed lock."""
        
        try:
            result = self.db.service_client.table("operation_locks").delete().eq(
                "id", lock.lock_id
            ).eq("holder_id", lock.holder_id).execute()
            
            if result.data:
                logger.info(f"Released lock {lock.lock_id} for {lock.lock_type.value}:{lock.resource_id}")
            else:
                logger.warning(f"Lock {lock.lock_id} was not found or already released")
                
        except Exception as e:
            logger.error(f"Failed to release distributed lock {lock.lock_id}: {e}")
    
    async def execute_atomic_transaction(
        self,
        operations: List[Callable],
        lock_type: LockType,
        resource_id: str,
        rollback_operations: Optional[List[Callable]] = None
    ) -> Any:
        """Execute multiple operations atomically with proper locking."""
        
        async with self.acquire_lock(lock_type, resource_id):
            try:
                # Execute all operations
                results = []
                for operation in operations:
                    if asyncio.iscoroutinefunction(operation):
                        result = await operation()
                    else:
                        result = operation()
                    results.append(result)
                
                return results
                
            except Exception as e:
                logger.error(f"Atomic transaction failed: {e}")
                
                # Execute rollback operations if provided
                if rollback_operations:
                    try:
                        for rollback_op in reversed(rollback_operations):
                            if asyncio.iscoroutinefunction(rollback_op):
                                await rollback_op()
                            else:
                                rollback_op()
                        logger.info("Rollback operations completed successfully")
                    except Exception as rollback_error:
                        logger.error(f"Rollback failed: {rollback_error}")
                
                raise
    
    async def handle_concurrent_rotation_advance(
        self,
        mypoolr_id: str,
        current_position: int,
        next_position: int
    ) -> bool:
        """Handle concurrent rotation advancement safely."""
        
        async with self.acquire_lock(
            LockType.ROTATION_ADVANCE,
            mypoolr_id,
            metadata={"current_position": current_position, "next_position": next_position}
        ):
            try:
                # Verify current state hasn't changed
                mypoolr_result = self.db.service_client.table("mypoolr").select("*").eq("id", mypoolr_id).execute()
                
                if not mypoolr_result.data:
                    raise ValueError(f"MyPoolr not found: {mypoolr_id}")
                
                mypoolr = mypoolr_result.data[0]
                
                # Check if position has changed since we started
                if mypoolr["current_rotation_position"] != current_position:
                    logger.warning(f"Rotation position changed during operation: expected {current_position}, got {mypoolr['current_rotation_position']}")
                    return False
                
                # Update rotation position atomically
                update_result = self.db.service_client.table("mypoolr").update({
                    "current_rotation_position": next_position,
                    "updated_at": datetime.utcnow().isoformat()
                }).eq("id", mypoolr_id).eq("current_rotation_position", current_position).execute()
                
                if update_result.data:
                    logger.info(f"Successfully advanced rotation from {current_position} to {next_position}")
                    return True
                else:
                    logger.warning("Failed to update rotation position - concurrent modification detected")
                    return False
                
            except Exception as e:
                logger.error(f"Failed to handle concurrent rotation advance: {e}")
                raise
    
    async def handle_concurrent_security_deposit_usage(
        self,
        member_id: str,
        amount_to_use: float,
        reason: str
    ) -> bool:
        """Handle concurrent security deposit usage safely."""
        
        async with self.acquire_lock(
            LockType.SECURITY_DEPOSIT,
            member_id,
            metadata={"amount_to_use": amount_to_use, "reason": reason}
        ):
            try:
                # Get current member state
                member_result = self.db.service_client.table("members").select("*").eq("id", member_id).execute()
                
                if not member_result.data:
                    raise ValueError(f"Member not found: {member_id}")
                
                member = member_result.data[0]
                current_deposit = float(member["security_deposit_amount"])
                
                # Check if sufficient deposit available
                if current_deposit < amount_to_use:
                    logger.error(f"Insufficient security deposit: available {current_deposit}, needed {amount_to_use}")
                    return False
                
                # Calculate new deposit amount
                new_deposit_amount = current_deposit - amount_to_use
                
                # Update member's security deposit atomically
                update_result = self.db.service_client.table("members").update({
                    "security_deposit_amount": new_deposit_amount,
                    "security_deposit_status": "used" if new_deposit_amount == 0 else "locked",
                    "updated_at": datetime.utcnow().isoformat()
                }).eq("id", member_id).eq("security_deposit_amount", current_deposit).execute()
                
                if update_result.data:
                    logger.info(f"Successfully used {amount_to_use} from security deposit for member {member_id}")
                    
                    # Record the usage transaction
                    transaction_data = {
                        "id": str(uuid4()),
                        "mypoolr_id": member["mypoolr_id"],
                        "from_member_id": member_id,
                        "to_member_id": None,
                        "amount": amount_to_use,
                        "transaction_type": "default_coverage",
                        "confirmation_status": "both_confirmed",
                        "metadata": json.dumps({"reason": reason, "auto_processed": True}),
                        "created_at": datetime.utcnow().isoformat()
                    }
                    
                    self.db.service_client.table("transactions").insert(transaction_data).execute()
                    
                    return True
                else:
                    logger.warning("Failed to update security deposit - concurrent modification detected")
                    return False
                
            except Exception as e:
                logger.error(f"Failed to handle concurrent security deposit usage: {e}")
                raise
    
    async def handle_concurrent_contribution_confirmation(
        self,
        transaction_id: str,
        confirming_party: str,  # "sender" or "recipient"
        member_id: str
    ) -> bool:
        """Handle concurrent contribution confirmation safely."""
        
        async with self.acquire_lock(
            LockType.TRANSACTION_WRITE,
            transaction_id,
            metadata={"confirming_party": confirming_party, "member_id": member_id}
        ):
            try:
                # Get current transaction state
                transaction_result = self.db.service_client.table("transactions").select("*").eq("id", transaction_id).execute()
                
                if not transaction_result.data:
                    raise ValueError(f"Transaction not found: {transaction_id}")
                
                transaction = transaction_result.data[0]
                current_status = transaction["confirmation_status"]
                
                # Determine new status based on confirming party and current status
                if confirming_party == "sender":
                    if current_status == "pending":
                        new_status = "sender_confirmed"
                        confirmation_field = "sender_confirmed_at"
                    elif current_status == "recipient_confirmed":
                        new_status = "both_confirmed"
                        confirmation_field = "sender_confirmed_at"
                    else:
                        logger.warning(f"Invalid sender confirmation for transaction {transaction_id} with status {current_status}")
                        return False
                        
                elif confirming_party == "recipient":
                    if current_status == "pending":
                        new_status = "recipient_confirmed"
                        confirmation_field = "recipient_confirmed_at"
                    elif current_status == "sender_confirmed":
                        new_status = "both_confirmed"
                        confirmation_field = "recipient_confirmed_at"
                    else:
                        logger.warning(f"Invalid recipient confirmation for transaction {transaction_id} with status {current_status}")
                        return False
                else:
                    raise ValueError(f"Invalid confirming party: {confirming_party}")
                
                # Update transaction atomically
                update_data = {
                    "confirmation_status": new_status,
                    confirmation_field: datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }
                
                update_result = self.db.service_client.table("transactions").update(update_data).eq(
                    "id", transaction_id
                ).eq("confirmation_status", current_status).execute()
                
                if update_result.data:
                    logger.info(f"Successfully confirmed transaction {transaction_id} by {confirming_party}")
                    return True
                else:
                    logger.warning("Failed to update transaction - concurrent modification detected")
                    return False
                
            except Exception as e:
                logger.error(f"Failed to handle concurrent contribution confirmation: {e}")
                raise
    
    async def get_active_locks(self, resource_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of active locks, optionally filtered by resource."""
        
        try:
            query = self.db.service_client.table("operation_locks").select("*").gt(
                "expires_at", datetime.utcnow().isoformat()
            )
            
            if resource_id:
                query = query.eq("resource_id", resource_id)
            
            result = query.execute()
            return result.data or []
            
        except Exception as e:
            logger.error(f"Failed to get active locks: {e}")
            return []
    
    async def force_release_lock(self, lock_id: str, reason: str = "Manual release") -> bool:
        """Force release a lock (admin operation)."""
        
        try:
            result = self.db.service_client.table("operation_locks").delete().eq("id", lock_id).execute()
            
            if result.data:
                logger.warning(f"Force released lock {lock_id}: {reason}")
                return True
            else:
                logger.warning(f"Lock {lock_id} not found for force release")
                return False
                
        except Exception as e:
            logger.error(f"Failed to force release lock {lock_id}: {e}")
            return False


class ConcurrencyError(Exception):
    """Exception raised when concurrent operation conflicts occur."""
    pass


class ConflictResolutionStrategy(Enum):
    """Strategies for resolving conflicts."""
    TIMESTAMP_BASED = "timestamp_based"
    ADMIN_PRIORITY = "admin_priority"
    FIRST_WINS = "first_wins"
    LAST_WINS = "last_wins"


class ConflictResolver:
    """Resolves conflicts in concurrent operations."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    async def resolve_rotation_conflict(
        self,
        mypoolr_id: str,
        conflicting_positions: List[int],
        strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.TIMESTAMP_BASED
    ) -> int:
        """Resolve rotation position conflicts."""
        
        try:
            # Get current MyPoolr state
            mypoolr_result = self.db.service_client.table("mypoolr").select("*").eq("id", mypoolr_id).execute()
            
            if not mypoolr_result.data:
                raise ValueError(f"MyPoolr not found: {mypoolr_id}")
            
            mypoolr = mypoolr_result.data[0]
            current_position = mypoolr["current_rotation_position"]
            
            if strategy == ConflictResolutionStrategy.TIMESTAMP_BASED:
                # Use the most recent valid position
                return max(conflicting_positions)
            elif strategy == ConflictResolutionStrategy.FIRST_WINS:
                return min(conflicting_positions)
            else:
                # Default to current database state
                return current_position
                
        except Exception as e:
            logger.error(f"Failed to resolve rotation conflict: {e}")
            raise
    
    async def detect_data_inconsistencies(self, mypoolr_id: str) -> List[Dict[str, Any]]:
        """Detect data inconsistencies in a MyPoolr group."""
        
        inconsistencies = []
        
        try:
            # Get MyPoolr and related data
            mypoolr_result = self.db.service_client.table("mypoolr").select("*").eq("id", mypoolr_id).execute()
            members_result = self.db.service_client.table("members").select("*").eq("mypoolr_id", mypoolr_id).execute()
            transactions_result = self.db.service_client.table("transactions").select("*").eq("mypoolr_id", mypoolr_id).execute()
            
            if not mypoolr_result.data:
                return inconsistencies
            
            mypoolr = mypoolr_result.data[0]
            members = members_result.data or []
            transactions = transactions_result.data or []
            
            # Check member count vs limit
            if len(members) > mypoolr["member_limit"]:
                inconsistencies.append({
                    "type": "member_limit_exceeded",
                    "description": f"Member count ({len(members)}) exceeds limit ({mypoolr['member_limit']})",
                    "severity": "high"
                })
            
            # Check rotation position validity
            active_members = [m for m in members if m["status"] == "active"]
            if mypoolr["current_rotation_position"] > len(active_members):
                inconsistencies.append({
                    "type": "invalid_rotation_position",
                    "description": f"Rotation position ({mypoolr['current_rotation_position']}) exceeds active member count ({len(active_members)})",
                    "severity": "high"
                })
            
            # Check security deposit consistency
            for member in members:
                if member["security_deposit_status"] == "confirmed" and float(member["security_deposit_amount"]) <= 0:
                    inconsistencies.append({
                        "type": "invalid_security_deposit",
                        "description": f"Member {member['id']} has confirmed status but zero deposit",
                        "severity": "medium"
                    })
            
            # Check transaction consistency
            for transaction in transactions:
                if transaction["confirmation_status"] == "both_confirmed":
                    if not transaction["sender_confirmed_at"] or not transaction["recipient_confirmed_at"]:
                        inconsistencies.append({
                            "type": "incomplete_confirmation_timestamps",
                            "description": f"Transaction {transaction['id']} marked as both_confirmed but missing timestamps",
                            "severity": "medium"
                        })
            
            return inconsistencies
            
        except Exception as e:
            logger.error(f"Failed to detect data inconsistencies: {e}")
            return []
    
    async def auto_correct_inconsistencies(self, mypoolr_id: str) -> Dict[str, Any]:
        """Automatically correct detected inconsistencies where possible."""
        
        corrections_made = []
        errors = []
        
        try:
            inconsistencies = await self.detect_data_inconsistencies(mypoolr_id)
            
            for inconsistency in inconsistencies:
                try:
                    if inconsistency["type"] == "invalid_rotation_position":
                        # Reset rotation position to 1
                        self.db.service_client.table("mypoolr").update({
                            "current_rotation_position": 1,
                            "updated_at": datetime.utcnow().isoformat()
                        }).eq("id", mypoolr_id).execute()
                        
                        corrections_made.append("Reset rotation position to 1")
                        
                    elif inconsistency["type"] == "incomplete_confirmation_timestamps":
                        # This would require more complex logic to determine correct timestamps
                        # For now, just log it
                        logger.warning(f"Cannot auto-correct incomplete confirmation timestamps for MyPoolr {mypoolr_id}")
                        
                except Exception as e:
                    errors.append(f"Failed to correct {inconsistency['type']}: {e}")
            
            return {
                "corrections_made": corrections_made,
                "errors": errors,
                "inconsistencies_found": len(inconsistencies)
            }
            
        except Exception as e:
            logger.error(f"Failed to auto-correct inconsistencies: {e}")
            return {"corrections_made": [], "errors": [str(e)], "inconsistencies_found": 0}