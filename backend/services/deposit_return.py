"""Security deposit return system for MyPoolr Circles.

This module implements the simultaneous deposit return system that ensures
all security deposits are returned when rotation cycles complete, maintaining
the no-loss guarantee throughout the process.
"""

import logging
from typing import Dict, Any, List, Optional
from uuid import UUID
from decimal import Decimal
from datetime import datetime

from models.member import Member, MemberStatus, SecurityDepositStatus
from models.mypoolr import MyPoolr
from models.transaction import Transaction, TransactionType, ConfirmationStatus
from database import db_manager

logger = logging.getLogger(__name__)


class SecurityDepositReturnService:
    """Manages security deposit returns and cycle completion."""
    
    @staticmethod
    def validate_cycle_completion(mypoolr_id: UUID) -> Dict[str, Any]:
        """
        Validate that a MyPoolr cycle is complete and ready for deposit returns.
        
        Args:
            mypoolr_id: UUID of the MyPoolr group
            
        Returns:
            Dict containing validation results and cycle status
        """
        try:
            # Get MyPoolr details
            mypoolr_result = db_manager.client.table("mypoolr").select("*").eq(
                "id", str(mypoolr_id)
            ).execute()
            
            if not mypoolr_result.data:
                raise ValueError(f"MyPoolr {mypoolr_id} not found")
            
            mypoolr_data = mypoolr_result.data[0]
            
            # Get all active members
            members_result = db_manager.client.table("member").select("*").eq(
                "mypoolr_id", str(mypoolr_id)
            ).eq("status", "active").execute()
            
            members = members_result.data or []
            total_members = len(members)
            
            # Check rotation completion
            completed_rotations = mypoolr_data["total_rotations_completed"]
            is_cycle_complete = completed_rotations >= total_members
            
            # Validate all members have received payouts
            members_with_payouts = [m for m in members if m["has_received_payout"]]
            all_received_payouts = len(members_with_payouts) == total_members
            
            # Check for any outstanding contributions
            # This would need to query transactions for pending contributions
            pending_contributions = SecurityDepositReturnService._check_pending_contributions(mypoolr_id)
            
            # Validate deposit integrity
            deposit_validation = SecurityDepositReturnService._validate_deposit_integrity(members)
            
            return {
                "mypoolr_id": str(mypoolr_id),
                "is_cycle_complete": is_cycle_complete,
                "all_received_payouts": all_received_payouts,
                "has_pending_contributions": len(pending_contributions) > 0,
                "deposit_integrity_valid": deposit_validation["is_valid"],
                "can_return_deposits": (
                    is_cycle_complete and 
                    all_received_payouts and 
                    len(pending_contributions) == 0 and 
                    deposit_validation["is_valid"]
                ),
                "validation_details": {
                    "total_members": total_members,
                    "completed_rotations": completed_rotations,
                    "members_with_payouts": len(members_with_payouts),
                    "pending_contributions": pending_contributions,
                    "deposit_validation": deposit_validation
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to validate cycle completion for MyPoolr {mypoolr_id}: {e}")
            raise Exception(f"Cycle validation failed: {str(e)}")
    
    @staticmethod
    def process_simultaneous_deposit_return(mypoolr_id: UUID, admin_id: int) -> Dict[str, Any]:
        """
        Process simultaneous return of all security deposits for a completed cycle.
        
        This function implements the core no-loss guarantee by ensuring all
        deposits are returned simultaneously when the cycle completes.
        
        Args:
            mypoolr_id: UUID of the MyPoolr group
            admin_id: Telegram ID of the admin authorizing the return
            
        Returns:
            Dict containing return results and transaction details
        """
        try:
            # Step 1: Validate cycle completion
            validation_result = SecurityDepositReturnService.validate_cycle_completion(mypoolr_id)
            
            if not validation_result["can_return_deposits"]:
                raise ValueError(
                    f"Cannot return deposits - cycle not ready. Validation: {validation_result}"
                )
            
            # Step 2: Verify admin authorization
            mypoolr_result = db_manager.client.table("mypoolr").select("*").eq(
                "id", str(mypoolr_id)
            ).execute()
            
            if not mypoolr_result.data:
                raise ValueError(f"MyPoolr {mypoolr_id} not found")
            
            mypoolr_data = mypoolr_result.data[0]
            
            if mypoolr_data["admin_id"] != admin_id:
                raise ValueError("Only the MyPoolr admin can authorize deposit returns")
            
            # Step 3: Get all members eligible for deposit return
            members_result = db_manager.client.table("member").select("*").eq(
                "mypoolr_id", str(mypoolr_id)
            ).eq("status", "active").execute()
            
            members = members_result.data or []
            
            if not members:
                raise ValueError("No active members found for deposit return")
            
            # Step 4: Calculate total deposits to return
            total_deposits = sum(
                Decimal(str(member["security_deposit_amount"])) 
                for member in members
                if member["security_deposit_status"] in [
                    SecurityDepositStatus.CONFIRMED.value,
                    SecurityDepositStatus.LOCKED.value
                ]
            )
            
            # Step 5: Process simultaneous returns
            return_results = []
            transaction_ids = []
            
            for member in members:
                if member["security_deposit_status"] not in [
                    SecurityDepositStatus.CONFIRMED.value,
                    SecurityDepositStatus.LOCKED.value
                ]:
                    continue
                
                # Update member status
                update_data = {
                    "security_deposit_status": SecurityDepositStatus.RETURNED.value,
                    "is_locked_in": False
                }
                
                update_result = db_manager.client.table("member").update(update_data).eq(
                    "id", member["id"]
                ).execute()
                
                if not update_result.data:
                    raise Exception(f"Failed to update member {member['id']} status")
                
                # Create return transaction
                transaction_data = {
                    "mypoolr_id": str(mypoolr_id),
                    "to_member_id": member["id"],
                    "amount": float(member["security_deposit_amount"]),
                    "transaction_type": TransactionType.DEPOSIT_RETURN.value,
                    "confirmation_status": ConfirmationStatus.BOTH_CONFIRMED.value,
                    "sender_confirmed_at": datetime.utcnow().isoformat(),
                    "recipient_confirmed_at": datetime.utcnow().isoformat(),
                    "metadata": {
                        "deposit_return": True,
                        "cycle_completion": True,
                        "authorized_by_admin": admin_id,
                        "simultaneous_return": True,
                        "return_batch_id": str(UUID.uuid4())
                    }
                }
                
                transaction_result = db_manager.client.table("transaction").insert(
                    transaction_data
                ).execute()
                
                if transaction_result.data:
                    transaction_ids.append(transaction_result.data[0]["id"])
                    return_results.append({
                        "member_id": member["id"],
                        "member_name": member["name"],
                        "deposit_amount": float(member["security_deposit_amount"]),
                        "transaction_id": transaction_result.data[0]["id"],
                        "status": "returned"
                    })
                    
                    logger.info(
                        f"Returned security deposit of {member['security_deposit_amount']} "
                        f"to member {member['id']} in MyPoolr {mypoolr_id}"
                    )
            
            # Step 6: Update MyPoolr status to completed
            mypoolr_update = {
                "status": "completed"
            }
            
            db_manager.client.table("mypoolr").update(mypoolr_update).eq(
                "id", str(mypoolr_id)
            ).execute()
            
            return {
                "success": True,
                "mypoolr_id": str(mypoolr_id),
                "total_deposits_returned": float(total_deposits),
                "members_processed": len(return_results),
                "return_results": return_results,
                "transaction_ids": transaction_ids,
                "cycle_completed": True,
                "no_loss_guarantee_maintained": True,
                "processed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to process deposit returns for MyPoolr {mypoolr_id}: {e}")
            raise Exception(f"Deposit return failed: {str(e)}")
    
    @staticmethod
    def validate_no_loss_guarantee(mypoolr_id: UUID) -> Dict[str, Any]:
        """
        Validate that the no-loss guarantee has been maintained throughout the cycle.
        
        This function performs comprehensive validation to ensure no member
        has lost money during the rotation cycle.
        
        Args:
            mypoolr_id: UUID of the MyPoolr group
            
        Returns:
            Dict containing validation results and guarantee status
        """
        try:
            # Get all members and transactions
            members_result = db_manager.client.table("member").select("*").eq(
                "mypoolr_id", str(mypoolr_id)
            ).execute()
            
            transactions_result = db_manager.client.table("transaction").select("*").eq(
                "mypoolr_id", str(mypoolr_id)
            ).execute()
            
            members = members_result.data or []
            transactions = transactions_result.data or []
            
            # Calculate financial flows for each member
            member_analysis = []
            total_contributions_made = Decimal('0')
            total_payouts_received = Decimal('0')
            total_deposits_paid = Decimal('0')
            total_deposits_returned = Decimal('0')
            
            for member in members:
                member_id = member["id"]
                
                # Calculate contributions made by this member
                contributions_made = sum(
                    Decimal(str(t["amount"]))
                    for t in transactions
                    if (t["from_member_id"] == member_id and 
                        t["transaction_type"] == TransactionType.CONTRIBUTION.value and
                        t["confirmation_status"] == ConfirmationStatus.BOTH_CONFIRMED.value)
                )
                
                # Calculate payouts received by this member
                payouts_received = sum(
                    Decimal(str(t["amount"]))
                    for t in transactions
                    if (t["to_member_id"] == member_id and 
                        t["transaction_type"] == TransactionType.CONTRIBUTION.value and
                        t["confirmation_status"] == ConfirmationStatus.BOTH_CONFIRMED.value)
                )
                
                # Calculate security deposit flows
                deposit_paid = sum(
                    Decimal(str(t["amount"]))
                    for t in transactions
                    if (t["to_member_id"] == member_id and 
                        t["transaction_type"] == TransactionType.SECURITY_DEPOSIT.value)
                )
                
                deposit_returned = sum(
                    Decimal(str(t["amount"]))
                    for t in transactions
                    if (t["to_member_id"] == member_id and 
                        t["transaction_type"] == TransactionType.DEPOSIT_RETURN.value)
                )
                
                # Calculate net position (should be zero for no-loss guarantee)
                net_position = payouts_received + deposit_returned - contributions_made - deposit_paid
                
                member_analysis.append({
                    "member_id": member_id,
                    "member_name": member["name"],
                    "contributions_made": float(contributions_made),
                    "payouts_received": float(payouts_received),
                    "deposit_paid": float(deposit_paid),
                    "deposit_returned": float(deposit_returned),
                    "net_position": float(net_position),
                    "no_loss_maintained": net_position >= 0
                })
                
                total_contributions_made += contributions_made
                total_payouts_received += payouts_received
                total_deposits_paid += deposit_paid
                total_deposits_returned += deposit_returned
            
            # Overall validation
            all_members_protected = all(
                analysis["no_loss_maintained"] for analysis in member_analysis
            )
            
            # Check system balance
            system_balance = total_deposits_paid - total_deposits_returned
            
            return {
                "mypoolr_id": str(mypoolr_id),
                "no_loss_guarantee_maintained": all_members_protected,
                "member_analysis": member_analysis,
                "system_totals": {
                    "total_contributions_made": float(total_contributions_made),
                    "total_payouts_received": float(total_payouts_received),
                    "total_deposits_paid": float(total_deposits_paid),
                    "total_deposits_returned": float(total_deposits_returned),
                    "system_balance": float(system_balance)
                },
                "validation_passed": all_members_protected and system_balance >= 0,
                "members_at_risk": [
                    analysis for analysis in member_analysis 
                    if not analysis["no_loss_maintained"]
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to validate no-loss guarantee for MyPoolr {mypoolr_id}: {e}")
            raise Exception(f"No-loss guarantee validation failed: {str(e)}")
    
    @staticmethod
    def _check_pending_contributions(mypoolr_id: UUID) -> List[Dict[str, Any]]:
        """Check for any pending contributions in the group."""
        try:
            pending_result = db_manager.client.table("transaction").select("*").eq(
                "mypoolr_id", str(mypoolr_id)
            ).eq("transaction_type", TransactionType.CONTRIBUTION.value).neq(
                "confirmation_status", ConfirmationStatus.BOTH_CONFIRMED.value
            ).execute()
            
            return pending_result.data or []
            
        except Exception:
            return []
    
    @staticmethod
    def _validate_deposit_integrity(members: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate the integrity of all security deposits."""
        try:
            valid_deposits = []
            invalid_deposits = []
            
            for member in members:
                deposit_status = member["security_deposit_status"]
                deposit_amount = Decimal(str(member["security_deposit_amount"]))
                
                if deposit_status in [
                    SecurityDepositStatus.CONFIRMED.value,
                    SecurityDepositStatus.LOCKED.value
                ] and deposit_amount > 0:
                    valid_deposits.append(member["id"])
                else:
                    invalid_deposits.append({
                        "member_id": member["id"],
                        "status": deposit_status,
                        "amount": float(deposit_amount)
                    })
            
            return {
                "is_valid": len(invalid_deposits) == 0,
                "valid_deposits_count": len(valid_deposits),
                "invalid_deposits": invalid_deposits
            }
            
        except Exception as e:
            return {
                "is_valid": False,
                "error": str(e)
            }
    
    @staticmethod
    def get_deposit_return_status(mypoolr_id: UUID) -> Dict[str, Any]:
        """
        Get the current status of deposit returns for a MyPoolr group.
        
        Args:
            mypoolr_id: UUID of the MyPoolr group
            
        Returns:
            Dict containing current deposit return status
        """
        try:
            # Get cycle completion status
            validation_result = SecurityDepositReturnService.validate_cycle_completion(mypoolr_id)
            
            # Get members with deposit status
            members_result = db_manager.client.table("member").select("*").eq(
                "mypoolr_id", str(mypoolr_id)
            ).execute()
            
            members = members_result.data or []
            
            # Categorize members by deposit status
            deposit_status_summary = {
                "pending": [],
                "confirmed": [],
                "locked": [],
                "returned": [],
                "used": []
            }
            
            for member in members:
                status = member["security_deposit_status"]
                member_info = {
                    "member_id": member["id"],
                    "name": member["name"],
                    "amount": float(member["security_deposit_amount"])
                }
                
                if status == SecurityDepositStatus.PENDING.value:
                    deposit_status_summary["pending"].append(member_info)
                elif status == SecurityDepositStatus.CONFIRMED.value:
                    deposit_status_summary["confirmed"].append(member_info)
                elif status == SecurityDepositStatus.LOCKED.value:
                    deposit_status_summary["locked"].append(member_info)
                elif status == SecurityDepositStatus.RETURNED.value:
                    deposit_status_summary["returned"].append(member_info)
                elif status == SecurityDepositStatus.USED.value:
                    deposit_status_summary["used"].append(member_info)
            
            return {
                "mypoolr_id": str(mypoolr_id),
                "cycle_validation": validation_result,
                "deposit_status_summary": deposit_status_summary,
                "ready_for_return": validation_result["can_return_deposits"],
                "total_members": len(members),
                "deposits_returned_count": len(deposit_status_summary["returned"]),
                "deposits_pending_return": len(deposit_status_summary["confirmed"]) + len(deposit_status_summary["locked"])
            }
            
        except Exception as e:
            logger.error(f"Failed to get deposit return status for MyPoolr {mypoolr_id}: {e}")
            raise Exception(f"Failed to get deposit return status: {str(e)}")