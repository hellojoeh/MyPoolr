"""Security lock-in mechanism service for MyPoolr Circles.

This module implements the security lock-in system that prevents members
from leaving the group after receiving their payout until the full cycle completes.
"""

import logging
from typing import Dict, Any, List, Optional
from uuid import UUID
from decimal import Decimal
from datetime import datetime

from models.member import Member, MemberStatus, SecurityDepositStatus
from models.mypoolr import MyPoolr
from database import db_manager

logger = logging.getLogger(__name__)


class SecurityLockInService:
    """Manages security lock-in mechanisms and early departure prevention."""
    
    @staticmethod
    def trigger_security_lockin(member_id: UUID, payout_amount: Decimal) -> Dict[str, Any]:
        """
        Trigger security lock-in when a member receives their payout.
        
        This function implements the core security mechanism that prevents
        members from leaving after receiving their rotation payout.
        
        Args:
            member_id: UUID of the member receiving payout
            payout_amount: Amount of the payout received
            
        Returns:
            Dict containing lock-in status and restrictions
        """
        try:
            # Get member details
            member_result = db_manager.client.table("member").select("*").eq(
                "id", str(member_id)
            ).execute()
            
            if not member_result.data:
                raise ValueError(f"Member {member_id} not found")
            
            member_data = member_result.data[0]
            
            # Verify member is eligible for lock-in
            if member_data["has_received_payout"]:
                raise ValueError("Member has already received payout and is locked in")
            
            if member_data["security_deposit_status"] != SecurityDepositStatus.CONFIRMED.value:
                raise ValueError("Member's security deposit must be confirmed before payout")
            
            # Apply security lock-in
            update_data = {
                "has_received_payout": True,
                "is_locked_in": True,
                "security_deposit_status": SecurityDepositStatus.LOCKED.value
            }
            
            update_result = db_manager.client.table("member").update(update_data).eq(
                "id", str(member_id)
            ).execute()
            
            if not update_result.data:
                raise Exception("Failed to apply security lock-in")
            
            # Log the lock-in event
            logger.info(f"Security lock-in applied to member {member_id} after payout of {payout_amount}")
            
            return {
                "success": True,
                "member_id": str(member_id),
                "locked_in": True,
                "security_deposit_locked": True,
                "restrictions": [
                    "Cannot leave group until full cycle completion",
                    "Security deposit locked until all rotations complete",
                    "Must continue contributing to remaining rotations"
                ],
                "payout_amount": float(payout_amount),
                "locked_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to apply security lock-in for member {member_id}: {e}")
            raise Exception(f"Security lock-in failed: {str(e)}")
    
    @staticmethod
    def validate_departure_eligibility(member_id: UUID) -> Dict[str, Any]:
        """
        Validate if a member is eligible to leave the group.
        
        This function checks all security restrictions and obligations
        to determine if a member can safely leave without compromising
        the group's financial integrity.
        
        Args:
            member_id: UUID of the member wanting to leave
            
        Returns:
            Dict containing eligibility status and any restrictions
        """
        try:
            # Get member details
            member_result = db_manager.client.table("member").select("*").eq(
                "id", str(member_id)
            ).execute()
            
            if not member_result.data:
                return {
                    "eligible": False,
                    "error": "Member not found"
                }
            
            member_data = member_result.data[0]
            
            # Get MyPoolr details for cycle status
            mypoolr_result = db_manager.client.table("mypoolr").select("*").eq(
                "id", member_data["mypoolr_id"]
            ).execute()
            
            if not mypoolr_result.data:
                return {
                    "eligible": False,
                    "error": "MyPoolr group not found"
                }
            
            mypoolr_data = mypoolr_result.data[0]
            restrictions = []
            required_actions = []
            
            # Check 1: Security lock-in status
            if member_data["is_locked_in"]:
                # Check if full cycle is complete
                total_members = db_manager.client.table("member").select("id").eq(
                    "mypoolr_id", member_data["mypoolr_id"]
                ).eq("status", "active").execute()
                
                total_member_count = len(total_members.data) if total_members.data else 0
                
                if mypoolr_data["total_rotations_completed"] < total_member_count:
                    restrictions.append("Security lock-in active - received payout")
                    required_actions.append("Wait for all rotations to complete")
            
            # Check 2: Security deposit status
            if member_data["security_deposit_status"] == SecurityDepositStatus.PENDING.value:
                restrictions.append("Security deposit not confirmed")
                required_actions.append("Complete security deposit payment")
            elif member_data["security_deposit_status"] == SecurityDepositStatus.USED.value:
                restrictions.append("Security deposit used for defaults")
                required_actions.append("Replenish security deposit")
            
            # Check 3: Outstanding contributions
            # This would need to check for any pending contributions
            # For now, we'll assume this is handled elsewhere
            
            # Determine eligibility
            eligible = len(restrictions) == 0
            
            return {
                "eligible": eligible,
                "member_id": str(member_id),
                "restrictions": restrictions,
                "required_actions": required_actions,
                "cycle_status": {
                    "total_members": total_member_count if 'total_member_count' in locals() else 0,
                    "completed_rotations": mypoolr_data["total_rotations_completed"],
                    "is_cycle_complete": mypoolr_data["total_rotations_completed"] >= (total_member_count if 'total_member_count' in locals() else 0)
                },
                "security_status": {
                    "deposit_status": member_data["security_deposit_status"],
                    "is_locked_in": member_data["is_locked_in"],
                    "has_received_payout": member_data["has_received_payout"]
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to validate departure eligibility for member {member_id}: {e}")
            return {
                "eligible": False,
                "error": f"Validation failed: {str(e)}"
            }
    
    @staticmethod
    def check_cycle_completion(mypoolr_id: UUID) -> Dict[str, Any]:
        """
        Check if a MyPoolr cycle is complete and members can be unlocked.
        
        Args:
            mypoolr_id: UUID of the MyPoolr group
            
        Returns:
            Dict containing cycle status and unlock eligibility
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
            
            total_members = len(members_result.data) if members_result.data else 0
            completed_rotations = mypoolr_data["total_rotations_completed"]
            
            # Check if cycle is complete
            is_complete = completed_rotations >= total_members
            
            # Get locked members count
            locked_members = [
                member for member in (members_result.data or [])
                if member["is_locked_in"]
            ]
            
            return {
                "mypoolr_id": str(mypoolr_id),
                "is_cycle_complete": is_complete,
                "total_members": total_members,
                "completed_rotations": completed_rotations,
                "remaining_rotations": max(0, total_members - completed_rotations),
                "locked_members_count": len(locked_members),
                "can_unlock_members": is_complete,
                "locked_member_ids": [member["id"] for member in locked_members]
            }
            
        except Exception as e:
            logger.error(f"Failed to check cycle completion for MyPoolr {mypoolr_id}: {e}")
            raise Exception(f"Cycle completion check failed: {str(e)}")
    
    @staticmethod
    def unlock_members_after_cycle_completion(mypoolr_id: UUID) -> Dict[str, Any]:
        """
        Unlock all members after cycle completion.
        
        This function should be called when all rotations are complete
        to release security deposits and remove lock-in restrictions.
        
        Args:
            mypoolr_id: UUID of the MyPoolr group
            
        Returns:
            Dict containing unlock results
        """
        try:
            # First check if cycle is actually complete
            cycle_status = SecurityLockInService.check_cycle_completion(mypoolr_id)
            
            if not cycle_status["can_unlock_members"]:
                raise ValueError("Cannot unlock members - cycle not complete")
            
            # Get all locked members
            locked_members_result = db_manager.client.table("member").select("*").eq(
                "mypoolr_id", str(mypoolr_id)
            ).eq("is_locked_in", True).execute()
            
            if not locked_members_result.data:
                return {
                    "success": True,
                    "message": "No locked members to unlock",
                    "unlocked_count": 0
                }
            
            unlocked_members = []
            
            # Unlock each member
            for member_data in locked_members_result.data:
                update_data = {
                    "is_locked_in": False,
                    "security_deposit_status": SecurityDepositStatus.RETURNED.value
                }
                
                update_result = db_manager.client.table("member").update(update_data).eq(
                    "id", member_data["id"]
                ).execute()
                
                if update_result.data:
                    unlocked_members.append(member_data["id"])
                    logger.info(f"Unlocked member {member_data['id']} after cycle completion")
            
            return {
                "success": True,
                "message": f"Successfully unlocked {len(unlocked_members)} members",
                "mypoolr_id": str(mypoolr_id),
                "unlocked_count": len(unlocked_members),
                "unlocked_member_ids": unlocked_members,
                "cycle_complete": True
            }
            
        except Exception as e:
            logger.error(f"Failed to unlock members for MyPoolr {mypoolr_id}: {e}")
            raise Exception(f"Member unlock failed: {str(e)}")
    
    @staticmethod
    def get_member_restrictions(member_id: UUID) -> Dict[str, Any]:
        """
        Get current restrictions and obligations for a member.
        
        Args:
            member_id: UUID of the member
            
        Returns:
            Dict containing all current restrictions and their reasons
        """
        try:
            # Get member details
            member_result = db_manager.client.table("member").select("*").eq(
                "id", str(member_id)
            ).execute()
            
            if not member_result.data:
                raise ValueError(f"Member {member_id} not found")
            
            member_data = member_result.data[0]
            
            restrictions = []
            obligations = []
            
            # Check lock-in status
            if member_data["is_locked_in"]:
                restrictions.append({
                    "type": "security_lockin",
                    "description": "Cannot leave group - received payout",
                    "reason": "Security lock-in active until cycle completion"
                })
            
            # Check security deposit status
            if member_data["security_deposit_status"] == SecurityDepositStatus.PENDING.value:
                obligations.append({
                    "type": "security_deposit",
                    "description": "Security deposit payment required",
                    "amount": member_data["security_deposit_amount"]
                })
            elif member_data["security_deposit_status"] == SecurityDepositStatus.USED.value:
                obligations.append({
                    "type": "deposit_replenishment",
                    "description": "Security deposit replenishment required",
                    "amount": member_data["security_deposit_amount"]
                })
            
            # Check payout status
            if member_data["has_received_payout"]:
                obligations.append({
                    "type": "continued_participation",
                    "description": "Must continue contributing until cycle completion",
                    "reason": "Received payout - locked in until all rotations complete"
                })
            
            return {
                "member_id": str(member_id),
                "has_restrictions": len(restrictions) > 0,
                "has_obligations": len(obligations) > 0,
                "restrictions": restrictions,
                "obligations": obligations,
                "can_leave": len(restrictions) == 0 and len(obligations) == 0,
                "status": {
                    "is_locked_in": member_data["is_locked_in"],
                    "has_received_payout": member_data["has_received_payout"],
                    "security_deposit_status": member_data["security_deposit_status"],
                    "member_status": member_data["status"]
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get restrictions for member {member_id}: {e}")
            raise Exception(f"Failed to get member restrictions: {str(e)}")