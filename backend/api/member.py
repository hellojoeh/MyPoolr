"""Member management API endpoints."""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from decimal import Decimal
from models import Member, MemberStatus, SecurityDepositStatus
from models.mypoolr import MyPoolr
from database import db_manager
from services.invitation_service import InvitationService
from services.security_deposit import SecurityDepositCalculator


router = APIRouter(prefix="/member", tags=["member"])


class JoinMemberRequest(BaseModel):
    """Request model for joining a MyPoolr via invitation."""
    invitation_token: str = Field(..., description="Invitation token from invitation link")
    telegram_id: int = Field(..., description="Telegram user ID")
    name: str = Field(..., min_length=1, max_length=100, description="Member's full name")
    phone_number: str = Field(..., min_length=10, max_length=15, description="Member's phone number")
    preferred_position: Optional[int] = Field(None, description="Preferred rotation position (optional)")


class SecurityDepositConfirmationRequest(BaseModel):
    """Request model for confirming security deposit payment."""
    member_id: str = Field(..., description="Member ID")
    admin_id: int = Field(..., description="Admin's Telegram ID for authorization")
    deposit_amount: Decimal = Field(..., description="Confirmed deposit amount")
    payment_reference: Optional[str] = Field(None, description="Payment reference or transaction ID")


class MemberResponse(BaseModel):
    """Response model for Member data."""
    id: str
    mypoolr_id: str
    telegram_id: int
    name: str
    phone_number: str
    rotation_position: int
    security_deposit_amount: Decimal
    security_deposit_status: str
    has_received_payout: bool
    is_locked_in: bool
    status: str


class JoinMemberResponse(BaseModel):
    """Response model for member join request."""
    member: MemberResponse
    security_deposit_details: dict
    next_steps: List[str]


@router.post("/join", response_model=JoinMemberResponse)
async def join_member(request: JoinMemberRequest):
    """
    Add a member to a MyPoolr group via invitation link.
    
    This endpoint handles the complete member registration workflow:
    1. Validates invitation token
    2. Calculates security deposit
    3. Creates member record
    4. Returns next steps for completion
    """
    try:
        # Step 1: Validate invitation token
        invitation_result = InvitationService.validate_invitation_token(request.invitation_token)
        
        if not invitation_result['valid']:
            raise HTTPException(status_code=400, detail=invitation_result['error'])
        
        mypoolr_details = invitation_result['mypoolr_details']
        mypoolr_id = UUID(mypoolr_details['id'])
        
        # Step 2: Check if user is already a member
        existing_member_result = db_manager.client.table("member").select("*").eq(
            "mypoolr_id", str(mypoolr_id)
        ).eq("telegram_id", request.telegram_id).execute()
        
        if existing_member_result.data:
            raise HTTPException(
                status_code=400, 
                detail="You are already a member of this MyPoolr group"
            )
        
        # Step 3: Calculate security deposit and assign position
        deposit_calculation = SecurityDepositCalculator.calculate_deposit_for_new_member(
            mypoolr_id, request.preferred_position
        )
        
        # Step 4: Create member record
        member = Member(
            mypoolr_id=mypoolr_id,
            telegram_id=request.telegram_id,
            name=request.name,
            phone_number=request.phone_number,
            rotation_position=deposit_calculation['assigned_position'],
            security_deposit_amount=deposit_calculation['deposit_amount'],
            security_deposit_status=SecurityDepositStatus.PENDING,
            status=MemberStatus.PENDING
        )
        
        # Insert into database
        result = db_manager.client.table("member").insert(
            member.dict()
        ).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to add member")
        
        created_member = result.data[0]
        
        # Step 5: Mark invitation as used
        InvitationService.use_invitation_token(request.invitation_token)
        
        # Step 6: Prepare response with next steps
        next_steps = [
            f"Pay security deposit of {deposit_calculation['deposit_amount']} {mypoolr_details.get('currency', 'KES')}",
            "Wait for admin confirmation of your security deposit",
            "You will be activated once your deposit is confirmed"
        ]
        
        return JoinMemberResponse(
            member=MemberResponse(**created_member),
            security_deposit_details={
                "required_amount": float(deposit_calculation['deposit_amount']),
                "assigned_position": deposit_calculation['assigned_position'],
                "calculation_details": deposit_calculation['calculation_details'],
                "payment_instructions": f"Please pay {deposit_calculation['deposit_amount']} as security deposit to the admin"
            },
            next_steps=next_steps
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to join member: {str(e)}")


@router.post("/confirm-deposit", response_model=MemberResponse)
async def confirm_security_deposit(request: SecurityDepositConfirmationRequest):
    """
    Confirm a member's security deposit payment (admin only).
    
    This endpoint allows admins to confirm that a member has paid their
    security deposit, which activates the member in the group.
    """
    try:
        # Step 1: Get member details
        member_result = db_manager.client.table("member").select("*").eq(
            "id", request.member_id
        ).execute()
        
        if not member_result.data:
            raise HTTPException(status_code=404, detail="Member not found")
        
        member_data = member_result.data[0]
        
        # Step 2: Verify admin authorization
        mypoolr_result = db_manager.client.table("mypoolr").select("*").eq(
            "id", member_data["mypoolr_id"]
        ).execute()
        
        if not mypoolr_result.data:
            raise HTTPException(status_code=404, detail="MyPoolr not found")
        
        mypoolr_data = mypoolr_result.data[0]
        
        if mypoolr_data["admin_id"] != request.admin_id:
            raise HTTPException(
                status_code=403, 
                detail="Only the MyPoolr admin can confirm security deposits"
            )
        
        # Step 3: Validate deposit amount
        if request.deposit_amount != Decimal(str(member_data["security_deposit_amount"])):
            raise HTTPException(
                status_code=400,
                detail=f"Deposit amount mismatch. Expected: {member_data['security_deposit_amount']}, Received: {request.deposit_amount}"
            )
        
        # Step 4: Update member status
        update_data = {
            "security_deposit_status": SecurityDepositStatus.CONFIRMED.value,
            "status": MemberStatus.ACTIVE.value
        }
        
        update_result = db_manager.client.table("member").update(update_data).eq(
            "id", request.member_id
        ).execute()
        
        if not update_result.data:
            raise HTTPException(status_code=500, detail="Failed to confirm deposit")
        
        # Step 5: Create transaction record for security deposit
        transaction_data = {
            "mypoolr_id": member_data["mypoolr_id"],
            "to_member_id": request.member_id,
            "amount": float(request.deposit_amount),
            "transaction_type": "security_deposit",
            "confirmation_status": "both_confirmed",
            "sender_confirmed_at": "now()",
            "recipient_confirmed_at": "now()",
            "metadata": {
                "payment_reference": request.payment_reference,
                "confirmed_by_admin": request.admin_id,
                "deposit_confirmation": True
            }
        }
        
        db_manager.client.table("transaction").insert(transaction_data).execute()
        
        updated_member = update_result.data[0]
        return MemberResponse(**updated_member)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to confirm deposit: {str(e)}")


class PayoutRequest(BaseModel):
    """Request model for processing member payout."""
    member_id: str = Field(..., description="Member ID receiving payout")
    admin_id: int = Field(..., description="Admin's Telegram ID for authorization")
    payout_amount: Decimal = Field(..., description="Payout amount")
    rotation_round: int = Field(..., description="Current rotation round")


class LeaveGroupRequest(BaseModel):
    """Request model for member leaving group."""
    member_id: str = Field(..., description="Member ID wanting to leave")
    telegram_id: int = Field(..., description="Member's Telegram ID for authorization")


@router.post("/process-payout")
async def process_member_payout(request: PayoutRequest):
    """
    Process a member's rotation payout and implement security lock-in.
    
    This endpoint handles payout processing and automatically locks the member's
    security deposit to prevent early departure until cycle completion.
    """
    try:
        # Step 1: Get member details
        member_result = db_manager.client.table("member").select("*").eq(
            "id", request.member_id
        ).execute()
        
        if not member_result.data:
            raise HTTPException(status_code=404, detail="Member not found")
        
        member_data = member_result.data[0]
        
        # Step 2: Verify admin authorization
        mypoolr_result = db_manager.client.table("mypoolr").select("*").eq(
            "id", member_data["mypoolr_id"]
        ).execute()
        
        if not mypoolr_result.data:
            raise HTTPException(status_code=404, detail="MyPoolr not found")
        
        mypoolr_data = mypoolr_result.data[0]
        
        if mypoolr_data["admin_id"] != request.admin_id:
            raise HTTPException(
                status_code=403, 
                detail="Only the MyPoolr admin can process payouts"
            )
        
        # Step 3: Validate member is eligible for payout
        if member_data["status"] != MemberStatus.ACTIVE.value:
            raise HTTPException(
                status_code=400,
                detail="Member must be active to receive payout"
            )
        
        if member_data["security_deposit_status"] != SecurityDepositStatus.CONFIRMED.value:
            raise HTTPException(
                status_code=400,
                detail="Member's security deposit must be confirmed before payout"
            )
        
        if member_data["has_received_payout"]:
            raise HTTPException(
                status_code=400,
                detail="Member has already received their payout for this cycle"
            )
        
        # Step 4: Implement security lock-in mechanism
        # Lock security deposit and restrict account
        update_data = {
            "has_received_payout": True,
            "is_locked_in": True,  # Prevent leaving until cycle completion
            "security_deposit_status": SecurityDepositStatus.LOCKED.value
        }
        
        update_result = db_manager.client.table("member").update(update_data).eq(
            "id", request.member_id
        ).execute()
        
        if not update_result.data:
            raise HTTPException(status_code=500, detail="Failed to process payout")
        
        # Step 5: Create transaction record for payout
        transaction_data = {
            "mypoolr_id": member_data["mypoolr_id"],
            "to_member_id": request.member_id,
            "amount": float(request.payout_amount),
            "transaction_type": "contribution",
            "confirmation_status": "both_confirmed",
            "sender_confirmed_at": "now()",
            "recipient_confirmed_at": "now()",
            "metadata": {
                "payout_processing": True,
                "rotation_round": request.rotation_round,
                "processed_by_admin": request.admin_id,
                "security_locked": True
            }
        }
        
        db_manager.client.table("transaction").insert(transaction_data).execute()
        
        return {
            "success": True,
            "message": "Payout processed successfully",
            "member_id": request.member_id,
            "security_status": "locked",
            "restrictions": [
                "Member cannot leave group until cycle completion",
                "Security deposit is locked until all rotations complete",
                "Member must continue contributing to remaining rotations"
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process payout: {str(e)}")


@router.post("/request-leave")
async def request_leave_group(request: LeaveGroupRequest):
    """
    Handle member request to leave group with security lock-in validation.
    
    This endpoint enforces early departure prevention for members who have
    received payouts or have outstanding obligations.
    """
    try:
        # Step 1: Get member details
        member_result = db_manager.client.table("member").select("*").eq(
            "id", request.member_id
        ).eq("telegram_id", request.telegram_id).execute()
        
        if not member_result.data:
            raise HTTPException(status_code=404, detail="Member not found or unauthorized")
        
        member_data = member_result.data[0]
        
        # Step 2: Check if member is locked in
        if member_data["is_locked_in"]:
            # Get MyPoolr details to check cycle status
            mypoolr_result = db_manager.client.table("mypoolr").select("*").eq(
                "id", member_data["mypoolr_id"]
            ).execute()
            
            if not mypoolr_result.data:
                raise HTTPException(status_code=404, detail="MyPoolr not found")
            
            mypoolr_data = mypoolr_result.data[0]
            
            # Check if full cycle is complete
            total_members = db_manager.client.table("member").select("id").eq(
                "mypoolr_id", member_data["mypoolr_id"]
            ).eq("status", "active").execute()
            
            total_member_count = len(total_members.data) if total_members.data else 0
            
            if mypoolr_data["total_rotations_completed"] < total_member_count:
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "Cannot leave group - security lock-in active",
                        "reason": "You have received your payout and must stay until all rotations complete",
                        "restrictions": [
                            "You cannot leave until the full rotation cycle completes",
                            "Your security deposit is locked until cycle completion",
                            "You must continue contributing to remaining member rotations"
                        ],
                        "cycle_status": {
                            "total_members": total_member_count,
                            "completed_rotations": mypoolr_data["total_rotations_completed"],
                            "remaining_rotations": total_member_count - mypoolr_data["total_rotations_completed"]
                        }
                    }
                )
        
        # Step 3: Check for outstanding obligations
        if member_data["security_deposit_status"] in [SecurityDepositStatus.PENDING.value, SecurityDepositStatus.USED.value]:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "Cannot leave group - outstanding obligations",
                    "reason": "You have pending security deposit requirements",
                    "required_actions": [
                        "Complete security deposit payment" if member_data["security_deposit_status"] == SecurityDepositStatus.PENDING.value else "Replenish used security deposit",
                        "Fulfill all financial obligations before leaving"
                    ]
                }
            )
        
        # Step 4: If member can leave, process departure
        if member_data["has_received_payout"] and not member_data["is_locked_in"]:
            # Member completed their obligations, can leave safely
            update_data = {
                "status": MemberStatus.REMOVED.value,
                "security_deposit_status": SecurityDepositStatus.RETURNED.value
            }
            
            db_manager.client.table("member").update(update_data).eq(
                "id", request.member_id
            ).execute()
            
            return {
                "success": True,
                "message": "Successfully left the group",
                "security_deposit_status": "returned"
            }
        else:
            # Member hasn't received payout yet, can leave with deposit return
            update_data = {
                "status": MemberStatus.REMOVED.value,
                "security_deposit_status": SecurityDepositStatus.RETURNED.value
            }
            
            db_manager.client.table("member").update(update_data).eq(
                "id", request.member_id
            ).execute()
            
            return {
                "success": True,
                "message": "Successfully left the group",
                "security_deposit_status": "returned"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process leave request: {str(e)}")


class CycleCompletionRequest(BaseModel):
    """Request model for completing a rotation cycle."""
    mypoolr_id: str = Field(..., description="MyPoolr ID")
    admin_id: int = Field(..., description="Admin's Telegram ID for authorization")


class DepositReturnRequest(BaseModel):
    """Request model for processing deposit returns."""
    mypoolr_id: str = Field(..., description="MyPoolr ID")
    admin_id: int = Field(..., description="Admin's Telegram ID for authorization")


@router.post("/complete-cycle")
async def complete_rotation_cycle(request: CycleCompletionRequest):
    """
    Complete a rotation cycle and prepare for deposit returns.
    
    This endpoint validates cycle completion and prepares the group
    for simultaneous security deposit returns.
    """
    try:
        from services.deposit_return import SecurityDepositReturnService
        
        # Validate cycle completion
        validation_result = SecurityDepositReturnService.validate_cycle_completion(
            UUID(request.mypoolr_id)
        )
        
        if not validation_result["can_return_deposits"]:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Cycle not ready for completion",
                    "validation_details": validation_result["validation_details"],
                    "required_actions": [
                        "Ensure all rotations are completed",
                        "Verify all members have received payouts",
                        "Resolve any pending contributions",
                        "Validate deposit integrity"
                    ]
                }
            )
        
        # Verify admin authorization
        mypoolr_result = db_manager.client.table("mypoolr").select("*").eq(
            "id", request.mypoolr_id
        ).execute()
        
        if not mypoolr_result.data:
            raise HTTPException(status_code=404, detail="MyPoolr not found")
        
        mypoolr_data = mypoolr_result.data[0]
        
        if mypoolr_data["admin_id"] != request.admin_id:
            raise HTTPException(
                status_code=403,
                detail="Only the MyPoolr admin can complete cycles"
            )
        
        return {
            "success": True,
            "message": "Cycle validation passed - ready for deposit returns",
            "mypoolr_id": request.mypoolr_id,
            "validation_result": validation_result,
            "next_step": "Process deposit returns using /member/return-deposits endpoint"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to complete cycle: {str(e)}")


@router.post("/return-deposits")
async def return_security_deposits(request: DepositReturnRequest):
    """
    Process simultaneous return of all security deposits for a completed cycle.
    
    This endpoint implements the core no-loss guarantee by ensuring all
    deposits are returned simultaneously when the cycle completes.
    """
    try:
        from services.deposit_return import SecurityDepositReturnService
        
        # Process simultaneous deposit returns
        return_result = SecurityDepositReturnService.process_simultaneous_deposit_return(
            UUID(request.mypoolr_id), request.admin_id
        )
        
        return return_result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to return deposits: {str(e)}")


@router.get("/deposit-status/{mypoolr_id}")
async def get_deposit_return_status(mypoolr_id: str):
    """
    Get the current status of deposit returns for a MyPoolr group.
    
    This endpoint provides comprehensive information about deposit
    return readiness and current status.
    """
    try:
        from services.deposit_return import SecurityDepositReturnService
        
        status_result = SecurityDepositReturnService.get_deposit_return_status(
            UUID(mypoolr_id)
        )
        
        return status_result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get deposit status: {str(e)}")


@router.post("/validate-no-loss")
async def validate_no_loss_guarantee(request: CycleCompletionRequest):
    """
    Validate that the no-loss guarantee has been maintained throughout the cycle.
    
    This endpoint performs comprehensive validation to ensure no member
    has lost money during the rotation cycle.
    """
    try:
        from services.deposit_return import SecurityDepositReturnService
        
        # Verify admin authorization
        mypoolr_result = db_manager.client.table("mypoolr").select("*").eq(
            "id", request.mypoolr_id
        ).execute()
        
        if not mypoolr_result.data:
            raise HTTPException(status_code=404, detail="MyPoolr not found")
        
        mypoolr_data = mypoolr_result.data[0]
        
        if mypoolr_data["admin_id"] != request.admin_id:
            raise HTTPException(
                status_code=403,
                detail="Only the MyPoolr admin can validate no-loss guarantee"
            )
        
        # Validate no-loss guarantee
        validation_result = SecurityDepositReturnService.validate_no_loss_guarantee(
            UUID(request.mypoolr_id)
        )
        
        return validation_result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to validate no-loss guarantee: {str(e)}")


@router.get("/mypoolr/{mypoolr_id}", response_model=List[MemberResponse])
async def get_mypoolr_members(mypoolr_id: UUID):
    """Get all members of a MyPoolr group."""
    try:
        result = db_manager.client.table("member").select("*").eq(
            "mypoolr_id", str(mypoolr_id)
        ).execute()
        
        return [MemberResponse(**member) for member in result.data]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{member_id}", response_model=MemberResponse)
async def get_member(member_id: UUID):
    """Get member by ID."""
    try:
        result = db_manager.client.table("member").select("*").eq(
            "id", str(member_id)
        ).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Member not found")
        
        return MemberResponse(**result.data[0])
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))