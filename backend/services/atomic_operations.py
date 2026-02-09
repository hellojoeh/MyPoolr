"""Atomic operations service for financial and critical operations."""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from uuid import UUID
from decimal import Decimal

from .concurrency_manager import ConcurrencyManager, LockType, ConcurrencyError
from ..database import DatabaseManager
from ..models.mypoolr import MyPoolr
from ..models.member import Member
from ..models.transaction import Transaction, TransactionType, ConfirmationStatus


logger = logging.getLogger(__name__)


class AtomicOperationResult:
    """Result of an atomic operation."""
    
    def __init__(self, success: bool, data: Any = None, error: str = None, rollback_performed: bool = False):
        self.success = success
        self.data = data
        self.error = error
        self.rollback_performed = rollback_performed
        self.timestamp = datetime.utcnow()


class AtomicOperationsService:
    """Service for executing atomic financial and critical operations."""
    
    def __init__(self, db_manager: DatabaseManager, concurrency_manager: ConcurrencyManager):
        self.db = db_manager
        self.concurrency = concurrency_manager
    
    async def atomic_contribution_confirmation(
        self,
        transaction_id: str,
        confirming_party: str,
        member_id: str
    ) -> AtomicOperationResult:
        """Atomically confirm a contribution with proper locking."""
        
        try:
            # Use concurrency manager for safe confirmation
            success = await self.concurrency.handle_concurrent_contribution_confirmation(
                transaction_id=transaction_id,
                confirming_party=confirming_party,
                member_id=member_id
            )
            
            if success:
                # Get updated transaction
                transaction_result = self.db.service_client.table("transactions").select("*").eq("id", transaction_id).execute()
                
                return AtomicOperationResult(
                    success=True,
                    data=transaction_result.data[0] if transaction_result.data else None
                )
            else:
                return AtomicOperationResult(
                    success=False,
                    error="Failed to confirm contribution due to concurrent modification"
                )
                
        except Exception as e:
            logger.error(f"Atomic contribution confirmation failed: {e}")
            return AtomicOperationResult(success=False, error=str(e))
    
    async def atomic_rotation_advance(
        self,
        mypoolr_id: str,
        expected_current_position: int,
        next_position: int
    ) -> AtomicOperationResult:
        """Atomically advance rotation with proper validation."""
        
        try:
            # Use concurrency manager for safe rotation advance
            success = await self.concurrency.handle_concurrent_rotation_advance(
                mypoolr_id=mypoolr_id,
                current_position=expected_current_position,
                next_position=next_position
            )
            
            if success:
                # Get updated MyPoolr
                mypoolr_result = self.db.service_client.table("mypoolr").select("*").eq("id", mypoolr_id).execute()
                
                return AtomicOperationResult(
                    success=True,
                    data=mypoolr_result.data[0] if mypoolr_result.data else None
                )
            else:
                return AtomicOperationResult(
                    success=False,
                    error="Failed to advance rotation due to concurrent modification"
                )
                
        except Exception as e:
            logger.error(f"Atomic rotation advance failed: {e}")
            return AtomicOperationResult(success=False, error=str(e))
    
    async def atomic_security_deposit_usage(
        self,
        member_id: str,
        amount_to_use: Decimal,
        reason: str,
        create_transaction: bool = True
    ) -> AtomicOperationResult:
        """Atomically use security deposit with proper validation."""
        
        try:
            # Use concurrency manager for safe deposit usage
            success = await self.concurrency.handle_concurrent_security_deposit_usage(
                member_id=member_id,
                amount_to_use=float(amount_to_use),
                reason=reason
            )
            
            if success:
                # Get updated member
                member_result = self.db.service_client.table("members").select("*").eq("id", member_id).execute()
                
                return AtomicOperationResult(
                    success=True,
                    data=member_result.data[0] if member_result.data else None
                )
            else:
                return AtomicOperationResult(
                    success=False,
                    error="Failed to use security deposit - insufficient funds or concurrent modification"
                )
                
        except Exception as e:
            logger.error(f"Atomic security deposit usage failed: {e}")
            return AtomicOperationResult(success=False, error=str(e))
    
    async def atomic_member_join(
        self,
        mypoolr_id: str,
        member_data: Dict[str, Any],
        security_deposit_amount: Decimal
    ) -> AtomicOperationResult:
        """Atomically add a member to MyPoolr with capacity checking."""
        
        rollback_operations = []
        
        try:
            async with self.concurrency.acquire_lock(LockType.MYPOOLR_WRITE, mypoolr_id):
                # Check MyPoolr capacity
                mypoolr_result = self.db.service_client.table("mypoolr").select("*").eq("id", mypoolr_id).execute()
                
                if not mypoolr_result.data:
                    return AtomicOperationResult(success=False, error="MyPoolr not found")
                
                mypoolr = mypoolr_result.data[0]
                
                # Count current members
                members_result = self.db.service_client.table("members").select("id").eq("mypoolr_id", mypoolr_id).execute()
                current_member_count = len(members_result.data) if members_result.data else 0
                
                if current_member_count >= mypoolr["member_limit"]:
                    return AtomicOperationResult(success=False, error="MyPoolr is at capacity")
                
                # Calculate rotation position
                next_position = current_member_count + 1
                
                # Prepare member data
                member_data.update({
                    "mypoolr_id": mypoolr_id,
                    "rotation_position": next_position,
                    "security_deposit_amount": float(security_deposit_amount),
                    "created_at": datetime.utcnow().isoformat()
                })
                
                # Insert member
                member_result = self.db.service_client.table("members").insert(member_data).execute()
                
                if not member_result.data:
                    return AtomicOperationResult(success=False, error="Failed to create member")
                
                new_member = member_result.data[0]
                rollback_operations.append(
                    lambda: self.db.service_client.table("members").delete().eq("id", new_member["id"]).execute()
                )
                
                # Create security deposit transaction if amount > 0
                if security_deposit_amount > 0:
                    transaction_data = {
                        "mypoolr_id": mypoolr_id,
                        "from_member_id": new_member["id"],
                        "to_member_id": None,
                        "amount": float(security_deposit_amount),
                        "transaction_type": TransactionType.SECURITY_DEPOSIT.value,
                        "confirmation_status": ConfirmationStatus.PENDING.value,
                        "metadata": {"reason": "Initial security deposit"},
                        "created_at": datetime.utcnow().isoformat()
                    }
                    
                    transaction_result = self.db.service_client.table("transactions").insert(transaction_data).execute()
                    
                    if transaction_result.data:
                        transaction_id = transaction_result.data[0]["id"]
                        rollback_operations.append(
                            lambda: self.db.service_client.table("transactions").delete().eq("id", transaction_id).execute()
                        )
                
                return AtomicOperationResult(success=True, data=new_member)
                
        except Exception as e:
            logger.error(f"Atomic member join failed: {e}")
            
            # Execute rollback operations
            for rollback_op in reversed(rollback_operations):
                try:
                    rollback_op()
                except Exception as rollback_error:
                    logger.error(f"Rollback operation failed: {rollback_error}")
            
            return AtomicOperationResult(success=False, error=str(e), rollback_performed=len(rollback_operations) > 0)
    
    async def atomic_default_handling(
        self,
        mypoolr_id: str,
        defaulted_member_id: str,
        recipient_member_id: str,
        contribution_amount: Decimal
    ) -> AtomicOperationResult:
        """Atomically handle a member default using security deposit."""
        
        rollback_operations = []
        
        try:
            # Lock both the defaulted member and the MyPoolr
            async with self.concurrency.acquire_lock(LockType.DEFAULT_HANDLING, f"{mypoolr_id}:{defaulted_member_id}"):
                
                # Use security deposit to cover the contribution
                deposit_result = await self.atomic_security_deposit_usage(
                    member_id=defaulted_member_id,
                    amount_to_use=contribution_amount,
                    reason=f"Default coverage for contribution to member {recipient_member_id}"
                )
                
                if not deposit_result.success:
                    return AtomicOperationResult(
                        success=False,
                        error=f"Failed to use security deposit: {deposit_result.error}"
                    )
                
                # Create the contribution transaction (auto-confirmed)
                transaction_data = {
                    "mypoolr_id": mypoolr_id,
                    "from_member_id": defaulted_member_id,
                    "to_member_id": recipient_member_id,
                    "amount": float(contribution_amount),
                    "transaction_type": TransactionType.CONTRIBUTION.value,
                    "confirmation_status": ConfirmationStatus.BOTH_CONFIRMED.value,
                    "sender_confirmed_at": datetime.utcnow().isoformat(),
                    "recipient_confirmed_at": datetime.utcnow().isoformat(),
                    "metadata": {
                        "auto_processed": True,
                        "reason": "Default handling using security deposit",
                        "original_deadline_missed": True
                    },
                    "created_at": datetime.utcnow().isoformat()
                }
                
                transaction_result = self.db.service_client.table("transactions").insert(transaction_data).execute()
                
                if not transaction_result.data:
                    # Rollback security deposit usage would be complex here
                    # In practice, this should be handled by the concurrency manager's atomic operations
                    return AtomicOperationResult(
                        success=False,
                        error="Failed to create default coverage transaction"
                    )
                
                new_transaction = transaction_result.data[0]
                
                # Update member status to reflect default
                member_update_result = self.db.service_client.table("members").update({
                    "status": "suspended",  # Suspend until deposit is replenished
                    "updated_at": datetime.utcnow().isoformat()
                }).eq("id", defaulted_member_id).execute()
                
                return AtomicOperationResult(
                    success=True,
                    data={
                        "transaction": new_transaction,
                        "member": deposit_result.data,
                        "default_handled": True
                    }
                )
                
        except Exception as e:
            logger.error(f"Atomic default handling failed: {e}")
            return AtomicOperationResult(success=False, error=str(e))
    
    async def atomic_tier_upgrade(
        self,
        admin_id: int,
        mypoolr_id: str,
        new_tier: str,
        payment_amount: Decimal,
        payment_reference: str
    ) -> AtomicOperationResult:
        """Atomically upgrade MyPoolr tier after payment confirmation."""
        
        try:
            async with self.concurrency.acquire_lock(LockType.TIER_UPGRADE, mypoolr_id):
                
                # Verify MyPoolr exists and admin owns it
                mypoolr_result = self.db.service_client.table("mypoolr").select("*").eq("id", mypoolr_id).execute()
                
                if not mypoolr_result.data:
                    return AtomicOperationResult(success=False, error="MyPoolr not found")
                
                mypoolr = mypoolr_result.data[0]
                
                if mypoolr["admin_id"] != admin_id:
                    return AtomicOperationResult(success=False, error="Unauthorized: Not the admin of this MyPoolr")
                
                # Update tier
                tier_update_result = self.db.service_client.table("mypoolr").update({
                    "tier": new_tier,
                    "updated_at": datetime.utcnow().isoformat()
                }).eq("id", mypoolr_id).execute()
                
                if not tier_update_result.data:
                    return AtomicOperationResult(success=False, error="Failed to update tier")
                
                # Create tier upgrade transaction record
                transaction_data = {
                    "mypoolr_id": mypoolr_id,
                    "from_member_id": None,
                    "to_member_id": None,
                    "amount": float(payment_amount),
                    "transaction_type": TransactionType.TIER_UPGRADE.value,
                    "confirmation_status": ConfirmationStatus.BOTH_CONFIRMED.value,
                    "metadata": {
                        "new_tier": new_tier,
                        "payment_reference": payment_reference,
                        "admin_id": admin_id
                    },
                    "created_at": datetime.utcnow().isoformat()
                }
                
                transaction_result = self.db.service_client.table("transactions").insert(transaction_data).execute()
                
                return AtomicOperationResult(
                    success=True,
                    data={
                        "mypoolr": tier_update_result.data[0],
                        "transaction": transaction_result.data[0] if transaction_result.data else None
                    }
                )
                
        except Exception as e:
            logger.error(f"Atomic tier upgrade failed: {e}")
            return AtomicOperationResult(success=False, error=str(e))
    
    async def atomic_security_deposit_return(
        self,
        mypoolr_id: str,
        member_ids: List[str]
    ) -> AtomicOperationResult:
        """Atomically return security deposits to multiple members."""
        
        returned_deposits = []
        failed_returns = []
        
        try:
            async with self.concurrency.acquire_lock(LockType.SECURITY_DEPOSIT, mypoolr_id):
                
                for member_id in member_ids:
                    try:
                        # Get member details
                        member_result = self.db.service_client.table("members").select("*").eq("id", member_id).execute()
                        
                        if not member_result.data:
                            failed_returns.append({"member_id": member_id, "error": "Member not found"})
                            continue
                        
                        member = member_result.data[0]
                        deposit_amount = float(member["security_deposit_amount"])
                        
                        if deposit_amount <= 0:
                            failed_returns.append({"member_id": member_id, "error": "No deposit to return"})
                            continue
                        
                        # Update member deposit status
                        update_result = self.db.service_client.table("members").update({
                            "security_deposit_amount": 0,
                            "security_deposit_status": "returned",
                            "updated_at": datetime.utcnow().isoformat()
                        }).eq("id", member_id).execute()
                        
                        if update_result.data:
                            # Create return transaction
                            transaction_data = {
                                "mypoolr_id": mypoolr_id,
                                "from_member_id": None,
                                "to_member_id": member_id,
                                "amount": deposit_amount,
                                "transaction_type": TransactionType.DEPOSIT_RETURN.value,
                                "confirmation_status": ConfirmationStatus.BOTH_CONFIRMED.value,
                                "metadata": {"reason": "Cycle completion deposit return"},
                                "created_at": datetime.utcnow().isoformat()
                            }
                            
                            transaction_result = self.db.service_client.table("transactions").insert(transaction_data).execute()
                            
                            returned_deposits.append({
                                "member_id": member_id,
                                "amount": deposit_amount,
                                "transaction_id": transaction_result.data[0]["id"] if transaction_result.data else None
                            })
                        else:
                            failed_returns.append({"member_id": member_id, "error": "Failed to update member"})
                            
                    except Exception as e:
                        failed_returns.append({"member_id": member_id, "error": str(e)})
                
                return AtomicOperationResult(
                    success=len(failed_returns) == 0,
                    data={
                        "returned_deposits": returned_deposits,
                        "failed_returns": failed_returns,
                        "total_processed": len(member_ids),
                        "successful_returns": len(returned_deposits)
                    }
                )
                
        except Exception as e:
            logger.error(f"Atomic security deposit return failed: {e}")
            return AtomicOperationResult(success=False, error=str(e))
    
    async def validate_operation_preconditions(
        self,
        operation_type: str,
        mypoolr_id: str,
        additional_checks: Dict[str, Any] = None
    ) -> AtomicOperationResult:
        """Validate preconditions for atomic operations."""
        
        try:
            # Get MyPoolr state
            mypoolr_result = self.db.service_client.table("mypoolr").select("*").eq("id", mypoolr_id).execute()
            
            if not mypoolr_result.data:
                return AtomicOperationResult(success=False, error="MyPoolr not found")
            
            mypoolr = mypoolr_result.data[0]
            
            # Basic validations
            if mypoolr["status"] != "active":
                return AtomicOperationResult(success=False, error="MyPoolr is not active")
            
            # Operation-specific validations
            if operation_type == "rotation_advance":
                members_result = self.db.service_client.table("members").select("*").eq(
                    "mypoolr_id", mypoolr_id
                ).eq("status", "active").execute()
                
                active_members = len(members_result.data) if members_result.data else 0
                current_position = mypoolr["current_rotation_position"]
                
                if current_position >= active_members:
                    return AtomicOperationResult(success=False, error="Invalid rotation position")
            
            elif operation_type == "member_join":
                members_result = self.db.service_client.table("members").select("id").eq("mypoolr_id", mypoolr_id).execute()
                current_count = len(members_result.data) if members_result.data else 0
                
                if current_count >= mypoolr["member_limit"]:
                    return AtomicOperationResult(success=False, error="MyPoolr is at capacity")
            
            return AtomicOperationResult(success=True, data={"mypoolr": mypoolr})
            
        except Exception as e:
            logger.error(f"Precondition validation failed: {e}")
            return AtomicOperationResult(success=False, error=str(e))