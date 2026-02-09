"""Invitation link generation and validation service."""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel
from database import db_manager


class InvitationLink(BaseModel):
    """Invitation link model."""
    id: str
    mypoolr_id: str
    token: str
    expires_at: datetime
    created_by: int  # admin telegram_id
    max_uses: Optional[int] = None
    current_uses: int = 0
    is_active: bool = True
    metadata: Dict[str, Any] = {}


class InvitationService:
    """Service for managing invitation links."""
    
    @staticmethod
    def generate_secure_token() -> str:
        """Generate a cryptographically secure token for invitation links."""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def create_invitation_link(
        mypoolr_id: UUID,
        admin_id: int,
        expires_in_hours: int = 168,  # 7 days default
        max_uses: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create a secure invitation link for a MyPoolr group.
        
        Args:
            mypoolr_id: UUID of the MyPoolr group
            admin_id: Telegram ID of the admin creating the link
            expires_in_hours: Hours until link expires (default 7 days)
            max_uses: Maximum number of times link can be used (None = unlimited)
            
        Returns:
            Dictionary containing link details and the invitation URL
        """
        try:
            # Get MyPoolr details to include in link
            mypoolr_result = db_manager.client.table("mypoolr").select("*").eq(
                "id", str(mypoolr_id)
            ).execute()
            
            if not mypoolr_result.data:
                raise ValueError("MyPoolr not found")
            
            mypoolr = mypoolr_result.data[0]
            
            # Verify admin owns this MyPoolr
            if mypoolr["admin_id"] != admin_id:
                raise ValueError("Only the admin can create invitation links")
            
            # Generate secure token
            token = InvitationService.generate_secure_token()
            expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
            
            # Create invitation record
            invitation_data = {
                "mypoolr_id": str(mypoolr_id),
                "token": token,
                "expires_at": expires_at.isoformat(),
                "created_by": admin_id,
                "max_uses": max_uses,
                "current_uses": 0,
                "is_active": True,
                "metadata": {
                    "mypoolr_name": mypoolr["name"],
                    "contribution_amount": float(mypoolr["contribution_amount"]),
                    "rotation_frequency": mypoolr["rotation_frequency"],
                    "member_limit": mypoolr["member_limit"],
                    "current_members": InvitationService._get_current_member_count(mypoolr_id)
                }
            }
            
            # Store in database (we'll need to create this table)
            result = db_manager.client.table("invitation_link").insert(
                invitation_data
            ).execute()
            
            if not result.data:
                raise Exception("Failed to create invitation link")
            
            created_link = result.data[0]
            
            # Generate the actual invitation URL (for Telegram deep linking)
            bot_username = "mypoolr_bot"  # This should come from config
            invitation_url = f"https://t.me/{bot_username}?start=join_{token}"
            
            return {
                "invitation_id": created_link["id"],
                "token": token,
                "invitation_url": invitation_url,
                "expires_at": expires_at,
                "max_uses": max_uses,
                "mypoolr_details": {
                    "id": str(mypoolr_id),
                    "name": mypoolr["name"],
                    "contribution_amount": mypoolr["contribution_amount"],
                    "rotation_frequency": mypoolr["rotation_frequency"],
                    "member_limit": mypoolr["member_limit"],
                    "current_members": invitation_data["metadata"]["current_members"]
                }
            }
            
        except Exception as e:
            raise Exception(f"Failed to create invitation link: {str(e)}")
    
    @staticmethod
    def validate_invitation_token(token: str) -> Dict[str, Any]:
        """
        Validate an invitation token and return MyPoolr details if valid.
        
        Args:
            token: The invitation token to validate
            
        Returns:
            Dictionary with validation result and MyPoolr details
        """
        try:
            # Get invitation link by token
            result = db_manager.client.table("invitation_link").select("*").eq(
                "token", token
            ).eq("is_active", True).execute()
            
            if not result.data:
                return {
                    "valid": False,
                    "error": "Invalid or expired invitation link"
                }
            
            invitation = result.data[0]
            
            # Check expiration
            expires_at = datetime.fromisoformat(invitation["expires_at"].replace('Z', '+00:00'))
            if datetime.utcnow().replace(tzinfo=expires_at.tzinfo) > expires_at:
                return {
                    "valid": False,
                    "error": "Invitation link has expired"
                }
            
            # Check usage limits
            if invitation["max_uses"] and invitation["current_uses"] >= invitation["max_uses"]:
                return {
                    "valid": False,
                    "error": "Invitation link has reached maximum usage limit"
                }
            
            # Get current MyPoolr details
            mypoolr_result = db_manager.client.table("mypoolr").select("*").eq(
                "id", invitation["mypoolr_id"]
            ).execute()
            
            if not mypoolr_result.data:
                return {
                    "valid": False,
                    "error": "MyPoolr group no longer exists"
                }
            
            mypoolr = mypoolr_result.data[0]
            
            # Check if group is still accepting members
            current_members = InvitationService._get_current_member_count(invitation["mypoolr_id"])
            if current_members >= mypoolr["member_limit"]:
                return {
                    "valid": False,
                    "error": "MyPoolr group is at full capacity"
                }
            
            return {
                "valid": True,
                "invitation_id": invitation["id"],
                "mypoolr_details": {
                    "id": invitation["mypoolr_id"],
                    "name": mypoolr["name"],
                    "admin_id": mypoolr["admin_id"],
                    "contribution_amount": mypoolr["contribution_amount"],
                    "rotation_frequency": mypoolr["rotation_frequency"],
                    "member_limit": mypoolr["member_limit"],
                    "current_members": current_members,
                    "available_slots": mypoolr["member_limit"] - current_members,
                    "tier": mypoolr["tier"]
                }
            }
            
        except Exception as e:
            return {
                "valid": False,
                "error": f"Error validating invitation: {str(e)}"
            }
    
    @staticmethod
    def use_invitation_token(token: str) -> bool:
        """
        Mark an invitation token as used (increment usage count).
        
        Args:
            token: The invitation token to mark as used
            
        Returns:
            True if successfully marked as used, False otherwise
        """
        try:
            # Get current invitation
            result = db_manager.client.table("invitation_link").select("*").eq(
                "token", token
            ).execute()
            
            if not result.data:
                return False
            
            invitation = result.data[0]
            new_uses = invitation["current_uses"] + 1
            
            # Update usage count
            update_result = db_manager.client.table("invitation_link").update({
                "current_uses": new_uses
            }).eq("id", invitation["id"]).execute()
            
            return bool(update_result.data)
            
        except Exception:
            return False
    
    @staticmethod
    def deactivate_invitation(invitation_id: str, admin_id: int) -> bool:
        """
        Deactivate an invitation link.
        
        Args:
            invitation_id: ID of the invitation to deactivate
            admin_id: Telegram ID of the admin (for authorization)
            
        Returns:
            True if successfully deactivated, False otherwise
        """
        try:
            # Verify admin owns this invitation
            result = db_manager.client.table("invitation_link").select("*").eq(
                "id", invitation_id
            ).eq("created_by", admin_id).execute()
            
            if not result.data:
                return False
            
            # Deactivate the invitation
            update_result = db_manager.client.table("invitation_link").update({
                "is_active": False
            }).eq("id", invitation_id).execute()
            
            return bool(update_result.data)
            
        except Exception:
            return False
    
    @staticmethod
    def get_mypoolr_invitations(mypoolr_id: UUID, admin_id: int) -> List[Dict[str, Any]]:
        """
        Get all invitation links for a MyPoolr group.
        
        Args:
            mypoolr_id: UUID of the MyPoolr group
            admin_id: Telegram ID of the admin (for authorization)
            
        Returns:
            List of invitation link details
        """
        try:
            result = db_manager.client.table("invitation_link").select("*").eq(
                "mypoolr_id", str(mypoolr_id)
            ).eq("created_by", admin_id).order("created_at", desc=True).execute()
            
            return result.data if result.data else []
            
        except Exception:
            return []
    
    @staticmethod
    def _get_current_member_count(mypoolr_id: UUID) -> int:
        """Get current active member count for a MyPoolr."""
        try:
            result = db_manager.client.table("member").select("id").eq(
                "mypoolr_id", str(mypoolr_id)
            ).eq("status", "active").execute()
            
            return len(result.data) if result.data else 0
            
        except Exception:
            return 0