"""Rotation management service for MyPoolr groups."""

from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime, timedelta
from decimal import Decimal
from database import db_manager
from models import TransactionType, ConfirmationStatus, MemberStatus


class RotationService:
    """Service for managing MyPoolr rotation logic."""
    
    @staticmethod
    async def check_rotation_completion(mypoolr_id: str, recipient_member_id: str) -> bool:
        """
        Check if all contributions for current rotation are complete.
        Returns True if rotation is complete and ready for advancement.
        """
        try:
            # Get all active members in the MyPoolr
            members_result = db_manager.client.table("member").select("*").eq(
                "mypoolr_id", mypoolr_id
            ).eq("status", MemberStatus.ACTIVE).execute()
            
            if not members_result.data:
                return False
            
            total_active_members = len(members_result.data)
            expected_contributions = total_active_members - 1  # All except recipient
            
            # Count confirmed contributions to this recipient
            contributions_result = db_manager.client.table("transaction").select("*").eq(
                "mypoolr_id", mypoolr_id
            ).eq("to_member_id", recipient_member_id).eq(
                "transaction_type", TransactionType.CONTRIBUTION
            ).eq("confirmation_status", ConfirmationStatus.BOTH_CONFIRMED).execute()
            
            confirmed_contributions = len(contributions_result.data) if contributions_result.data else 0
            
            return confirmed_contributions >= expected_contributions
            
        except Exception as e:
            print(f"Error checking rotation completion: {str(e)}")
            return False
    
    @staticmethod
    async def advance_rotation(mypoolr_id: str) -> Dict[str, Any]:
        """
        Advance to the next rotation in the schedule.
        Returns information about the advancement.
        """
        try:
            # Get current MyPoolr state
            mypoolr_result = db_manager.client.table("mypoolr").select("*").eq(
                "id", mypoolr_id
            ).execute()
            
            if not mypoolr_result.data:
                raise ValueError("MyPoolr not found")
            
            mypoolr = mypoolr_result.data[0]
            current_position = mypoolr.get("current_rotation_position", 0)
            
            # Get all active members ordered by rotation position
            members_result = db_manager.client.table("member").select("*").eq(
                "mypoolr_id", mypoolr_id
            ).eq("status", MemberStatus.ACTIVE).order("rotation_position").execute()
            
            if not members_result.data:
                raise ValueError("No active members found")
            
            members = members_result.data
            total_members = len(members)
            
            # Calculate next position
            next_position = (current_position + 1) % total_members
            next_member = members[next_position]
            
            # Check if we've completed a full cycle
            completed_rotations = mypoolr.get("total_rotations_completed", 0)
            if next_position == 0:  # Back to first member
                completed_rotations += 1
            
            # Update MyPoolr with new rotation position
            update_result = db_manager.client.table("mypoolr").update({
                "current_rotation_position": next_position,
                "total_rotations_completed": completed_rotations,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", mypoolr_id).execute()
            
            if not update_result.data:
                raise ValueError("Failed to update MyPoolr rotation position")
            
            return {
                "success": True,
                "previous_position": current_position,
                "new_position": next_position,
                "next_recipient": {
                    "member_id": next_member["id"],
                    "name": next_member["name"],
                    "rotation_position": next_member["rotation_position"]
                },
                "completed_rotations": completed_rotations,
                "is_cycle_complete": next_position == 0
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    async def get_current_rotation_recipient(mypoolr_id: str) -> Optional[Dict[str, Any]]:
        """Get the current rotation recipient for a MyPoolr."""
        try:
            # Get current MyPoolr state
            mypoolr_result = db_manager.client.table("mypoolr").select("*").eq(
                "id", mypoolr_id
            ).execute()
            
            if not mypoolr_result.data:
                return None
            
            mypoolr = mypoolr_result.data[0]
            current_position = mypoolr.get("current_rotation_position", 0)
            
            # Get all active members ordered by rotation position
            members_result = db_manager.client.table("member").select("*").eq(
                "mypoolr_id", mypoolr_id
            ).eq("status", MemberStatus.ACTIVE).order("rotation_position").execute()
            
            if not members_result.data or current_position >= len(members_result.data):
                return None
            
            current_recipient = members_result.data[current_position]
            
            return {
                "member_id": current_recipient["id"],
                "name": current_recipient["name"],
                "telegram_id": current_recipient["telegram_id"],
                "rotation_position": current_recipient["rotation_position"],
                "position_in_cycle": current_position
            }
            
        except Exception as e:
            print(f"Error getting current rotation recipient: {str(e)}")
            return None
    
    @staticmethod
    async def get_rotation_schedule(mypoolr_id: str) -> List[Dict[str, Any]]:
        """Get the complete rotation schedule for a MyPoolr."""
        try:
            # Get MyPoolr details
            mypoolr_result = db_manager.client.table("mypoolr").select("*").eq(
                "id", mypoolr_id
            ).execute()
            
            if not mypoolr_result.data:
                return []
            
            mypoolr = mypoolr_result.data[0]
            current_position = mypoolr.get("current_rotation_position", 0)
            
            # Get all active members ordered by rotation position
            members_result = db_manager.client.table("member").select("*").eq(
                "mypoolr_id", mypoolr_id
            ).eq("status", MemberStatus.ACTIVE).order("rotation_position").execute()
            
            if not members_result.data:
                return []
            
            schedule = []
            for i, member in enumerate(members_result.data):
                is_current = i == current_position
                is_completed = i < current_position or (current_position == 0 and mypoolr.get("total_rotations_completed", 0) > 0)
                
                schedule.append({
                    "position": i,
                    "member_id": member["id"],
                    "name": member["name"],
                    "telegram_id": member["telegram_id"],
                    "rotation_position": member["rotation_position"],
                    "is_current": is_current,
                    "is_completed": is_completed,
                    "status": "current" if is_current else ("completed" if is_completed else "pending")
                })
            
            return schedule
            
        except Exception as e:
            print(f"Error getting rotation schedule: {str(e)}")
            return []
    
    @staticmethod
    async def validate_rotation_advancement(mypoolr_id: str) -> Dict[str, Any]:
        """
        Validate if rotation can be advanced.
        Returns validation result with details.
        """
        try:
            # Get current recipient
            current_recipient = await RotationService.get_current_rotation_recipient(mypoolr_id)
            if not current_recipient:
                return {
                    "can_advance": False,
                    "reason": "No current recipient found"
                }
            
            # Check if current rotation is complete
            is_complete = await RotationService.check_rotation_completion(
                mypoolr_id, current_recipient["member_id"]
            )
            
            if not is_complete:
                # Get pending contributions count
                members_result = db_manager.client.table("member").select("*").eq(
                    "mypoolr_id", mypoolr_id
                ).eq("status", MemberStatus.ACTIVE).execute()
                
                contributions_result = db_manager.client.table("transaction").select("*").eq(
                    "mypoolr_id", mypoolr_id
                ).eq("to_member_id", current_recipient["member_id"]).eq(
                    "transaction_type", TransactionType.CONTRIBUTION
                ).eq("confirmation_status", ConfirmationStatus.BOTH_CONFIRMED).execute()
                
                total_members = len(members_result.data) if members_result.data else 0
                confirmed_contributions = len(contributions_result.data) if contributions_result.data else 0
                expected_contributions = total_members - 1
                pending_contributions = expected_contributions - confirmed_contributions
                
                return {
                    "can_advance": False,
                    "reason": f"Rotation incomplete: {pending_contributions} contributions pending",
                    "current_recipient": current_recipient,
                    "confirmed_contributions": confirmed_contributions,
                    "expected_contributions": expected_contributions,
                    "pending_contributions": pending_contributions
                }
            
            return {
                "can_advance": True,
                "current_recipient": current_recipient
            }
            
        except Exception as e:
            return {
                "can_advance": False,
                "reason": f"Validation error: {str(e)}"
            }