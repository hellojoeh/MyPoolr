"""MyPoolr management API endpoints."""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, validator
from models import MyPoolr, RotationFrequency, TierLevel
from database import db_manager
from services.tier_management import TierConfiguration, TierValidationError, TierManagementService
from services.invitation_service import InvitationService


router = APIRouter(prefix="/mypoolr", tags=["mypoolr"])


class CreateMyPoolrRequest(BaseModel):
    """Request model for creating a MyPoolr."""
    name: str
    admin_id: int
    contribution_amount: float
    rotation_frequency: RotationFrequency
    member_limit: int
    tier: TierLevel = TierLevel.STARTER
    
    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Name cannot be empty')
        if len(v) > 100:
            raise ValueError('Name cannot exceed 100 characters')
        return v.strip()
    
    @validator('contribution_amount')
    def validate_contribution_amount(cls, v):
        if v <= 0:
            raise ValueError('Contribution amount must be greater than 0')
        return v
    
    @validator('member_limit')
    def validate_member_limit_range(cls, v):
        if v < 2:
            raise ValueError('Member limit must be at least 2')
        if v > 100:
            raise ValueError('Member limit cannot exceed 100')
        return v


class MyPoolrResponse(BaseModel):
    """Response model for MyPoolr data."""
    id: str
    name: str
    admin_id: int
    contribution_amount: float
    rotation_frequency: str
    member_limit: int
    tier: str
    status: str
    current_rotation_position: int
    total_rotations_completed: int


class CreateInvitationRequest(BaseModel):
    """Request model for creating invitation links."""
    mypoolr_id: str
    admin_id: int
    expires_in_hours: int = 168  # 7 days default
    max_uses: Optional[int] = None
    
    @validator('expires_in_hours')
    def validate_expiry(cls, v):
        if v < 1:
            raise ValueError('Expiry must be at least 1 hour')
        if v > 8760:  # 1 year
            raise ValueError('Expiry cannot exceed 1 year')
        return v
    
    @validator('max_uses')
    def validate_max_uses(cls, v):
        if v is not None and v < 1:
            raise ValueError('Max uses must be at least 1')
        return v


class ValidateInvitationRequest(BaseModel):
    """Request model for validating invitation tokens."""
    token: str


@router.post("/create", response_model=MyPoolrResponse)
async def create_mypoolr(request: CreateMyPoolrRequest):
    """Create a new MyPoolr savings group with tier validation."""
    try:
        # Initialize tier management service
        tier_service = TierManagementService(db_manager)
        
        # Validate tier-based member limit
        tier_features = tier_service.get_tier_features(request.tier)
        if request.member_limit > tier_features.max_members_per_group:
            raise HTTPException(
                status_code=400, 
                detail=f"Member limit {request.member_limit} exceeds tier {request.tier.value} maximum of {tier_features.max_members_per_group}"
            )
        
        # Check if admin can create another group based on tier
        can_create = await tier_service.validate_tier_limits(request.admin_id, "create_group")
        if not can_create:
            raise HTTPException(
                status_code=400,
                detail=f"Tier {request.tier.value} group creation limit reached"
            )
        
        # Validate rotation frequency (ensure it's a valid enum value)
        if request.rotation_frequency not in [freq.value for freq in RotationFrequency]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid rotation frequency. Must be one of: {[freq.value for freq in RotationFrequency]}"
            )
        
        # Create MyPoolr instance
        mypoolr = MyPoolr(
            name=request.name,
            admin_id=request.admin_id,
            contribution_amount=request.contribution_amount,
            rotation_frequency=request.rotation_frequency,
            member_limit=request.member_limit,
            tier=request.tier
        )
        
        # Insert into database
        result = db_manager.client.table("mypoolr").insert(
            mypoolr.dict()
        ).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create MyPoolr")
        
        created_mypoolr = result.data[0]
        return MyPoolrResponse(**created_mypoolr)
        
    except HTTPException:
        raise
    except TierValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{mypoolr_id}", response_model=MyPoolrResponse)
async def get_mypoolr(mypoolr_id: UUID):
    """Get MyPoolr by ID."""
    try:
        result = db_manager.client.table("mypoolr").select("*").eq(
            "id", str(mypoolr_id)
        ).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="MyPoolr not found")
        
        return MyPoolrResponse(**result.data[0])
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/{admin_id}", response_model=List[MyPoolrResponse])
async def get_admin_mypoolrs(admin_id: int):
    """Get all MyPoolrs for an admin."""
    try:
        result = db_manager.client.table("mypoolr").select("*").eq(
            "admin_id", admin_id
        ).execute()
        
        return [MyPoolrResponse(**mypoolr) for mypoolr in result.data]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{mypoolr_id}/capacity", response_model=dict)
async def check_mypoolr_capacity(mypoolr_id: UUID):
    """Check MyPoolr member capacity and availability."""
    try:
        # Get MyPoolr details
        mypoolr_result = db_manager.client.table("mypoolr").select("*").eq(
            "id", str(mypoolr_id)
        ).execute()
        
        if not mypoolr_result.data:
            raise HTTPException(status_code=404, detail="MyPoolr not found")
        
        mypoolr = mypoolr_result.data[0]
        
        # Get current member count
        members_result = db_manager.client.table("member").select("id").eq(
            "mypoolr_id", str(mypoolr_id)
        ).eq("status", "active").execute()
        
        current_members = len(members_result.data) if members_result.data else 0
        member_limit = mypoolr["member_limit"]
        
        return {
            "mypoolr_id": str(mypoolr_id),
            "current_members": current_members,
            "member_limit": member_limit,
            "available_slots": member_limit - current_members,
            "is_full": current_members >= member_limit,
            "can_add_members": current_members < member_limit
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{mypoolr_id}/validate-member-addition")
async def validate_member_addition(mypoolr_id: UUID):
    """Validate if a new member can be added to the MyPoolr."""
    try:
        capacity_info = await check_mypoolr_capacity(mypoolr_id)
        
        if capacity_info["is_full"]:
            raise HTTPException(
                status_code=400,
                detail=f"MyPoolr is at full capacity ({capacity_info['member_limit']} members)"
            )
        
        return {
            "can_add_member": True,
            "available_slots": capacity_info["available_slots"],
            "message": f"Can add {capacity_info['available_slots']} more member(s)"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Invitation Link Management Endpoints

@router.post("/{mypoolr_id}/invitation", response_model=dict)
async def create_invitation_link(mypoolr_id: UUID, request: CreateInvitationRequest):
    """Create a secure invitation link for a MyPoolr group."""
    try:
        # Verify the mypoolr_id matches the request
        if str(mypoolr_id) != request.mypoolr_id:
            raise HTTPException(status_code=400, detail="MyPoolr ID mismatch")
        
        invitation_details = InvitationService.create_invitation_link(
            mypoolr_id=mypoolr_id,
            admin_id=request.admin_id,
            expires_in_hours=request.expires_in_hours,
            max_uses=request.max_uses
        )
        
        return invitation_details
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/invitation/validate", response_model=dict)
async def validate_invitation_token(request: ValidateInvitationRequest):
    """Validate an invitation token and return MyPoolr details."""
    try:
        validation_result = InvitationService.validate_invitation_token(request.token)
        
        if not validation_result["valid"]:
            raise HTTPException(status_code=400, detail=validation_result["error"])
        
        return validation_result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/invitation/{token}/use")
async def use_invitation_token(token: str):
    """Mark an invitation token as used."""
    try:
        success = InvitationService.use_invitation_token(token)
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to use invitation token")
        
        return {"success": True, "message": "Invitation token used successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{mypoolr_id}/invitations")
async def get_mypoolr_invitations(mypoolr_id: UUID, admin_id: int):
    """Get all invitation links for a MyPoolr group."""
    try:
        invitations = InvitationService.get_mypoolr_invitations(mypoolr_id, admin_id)
        
        return {
            "mypoolr_id": str(mypoolr_id),
            "invitations": invitations
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/invitation/{invitation_id}")
async def deactivate_invitation(invitation_id: str, admin_id: int):
    """Deactivate an invitation link."""
    try:
        success = InvitationService.deactivate_invitation(invitation_id, admin_id)
        
        if not success:
            raise HTTPException(
                status_code=400, 
                detail="Failed to deactivate invitation or unauthorized"
            )
        
        return {"success": True, "message": "Invitation deactivated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))