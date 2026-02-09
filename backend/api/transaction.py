"""Transaction management API endpoints."""

from typing import List, Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from models import Transaction, TransactionType, ConfirmationStatus
from database import db_manager
from services.rotation_service import RotationService


router = APIRouter(prefix="/transaction", tags=["transaction"])


class CreateTransactionRequest(BaseModel):
    """Request model for creating a transaction."""
    mypoolr_id: str
    from_member_id: Optional[str] = None
    to_member_id: Optional[str] = None
    amount: float
    transaction_type: TransactionType
    notes: Optional[str] = None


class InitiateContributionRequest(BaseModel):
    """Request model for initiating a contribution."""
    mypoolr_id: str
    from_member_id: str
    to_member_id: str
    amount: float
    notes: Optional[str] = None


class ConfirmTransactionRequest(BaseModel):
    """Request model for confirming a transaction."""
    transaction_id: str
    confirming_member_id: str
    confirmation_type: str  # "sender" or "recipient"


class TransactionResponse(BaseModel):
    """Response model for Transaction data."""
    id: str
    mypoolr_id: str
    from_member_id: Optional[str]
    to_member_id: Optional[str]
    amount: float
    transaction_type: str
    confirmation_status: str
    sender_confirmed_at: Optional[str]
    recipient_confirmed_at: Optional[str]
    notes: Optional[str]


@router.post("/create", response_model=TransactionResponse)
async def create_transaction(request: CreateTransactionRequest):
    """Create a new transaction."""
    try:
        # Create Transaction instance
        transaction = Transaction(
            mypoolr_id=UUID(request.mypoolr_id),
            from_member_id=UUID(request.from_member_id) if request.from_member_id else None,
            to_member_id=UUID(request.to_member_id) if request.to_member_id else None,
            amount=request.amount,
            transaction_type=request.transaction_type,
            notes=request.notes
        )
        
        # Insert into database
        result = db_manager.client.table("transaction").insert(
            transaction.dict()
        ).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create transaction")
        
        created_transaction = result.data[0]
        return TransactionResponse(**created_transaction)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/contribution/initiate", response_model=TransactionResponse)
async def initiate_contribution(request: InitiateContributionRequest):
    """Initiate a contribution transaction requiring dual confirmation."""
    try:
        # Validate that both members exist and belong to the MyPoolr
        from_member_result = db_manager.client.table("member").select("*").eq(
            "id", request.from_member_id
        ).eq("mypoolr_id", request.mypoolr_id).execute()
        
        to_member_result = db_manager.client.table("member").select("*").eq(
            "id", request.to_member_id
        ).eq("mypoolr_id", request.mypoolr_id).execute()
        
        if not from_member_result.data:
            raise HTTPException(status_code=404, detail="Sender member not found in this MyPoolr")
        
        if not to_member_result.data:
            raise HTTPException(status_code=404, detail="Recipient member not found in this MyPoolr")
        
        # Create contribution transaction
        transaction = Transaction(
            mypoolr_id=UUID(request.mypoolr_id),
            from_member_id=UUID(request.from_member_id),
            to_member_id=UUID(request.to_member_id),
            amount=request.amount,
            transaction_type=TransactionType.CONTRIBUTION,
            confirmation_status=ConfirmationStatus.PENDING,
            notes=request.notes
        )
        
        # Insert into database
        result = db_manager.client.table("transaction").insert(
            transaction.dict()
        ).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to initiate contribution")
        
        created_transaction = result.data[0]
        return TransactionResponse(**created_transaction)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/confirm")
async def confirm_transaction(request: ConfirmTransactionRequest):
    """Confirm a transaction by sender or recipient."""
    try:
        # Get current transaction
        result = db_manager.client.table("transaction").select("*").eq(
            "id", request.transaction_id
        ).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        transaction = result.data[0]
        
        # Validate that the confirming member is authorized
        if request.confirmation_type == "sender":
            if str(transaction.get("from_member_id")) != request.confirming_member_id:
                raise HTTPException(status_code=403, detail="Only the sender can provide sender confirmation")
        elif request.confirmation_type == "recipient":
            if str(transaction.get("to_member_id")) != request.confirming_member_id:
                raise HTTPException(status_code=403, detail="Only the recipient can provide recipient confirmation")
        else:
            raise HTTPException(status_code=400, detail="Invalid confirmation type. Must be 'sender' or 'recipient'")
        
        # Check if already confirmed by this party
        if request.confirmation_type == "sender" and transaction.get("sender_confirmed_at"):
            raise HTTPException(status_code=400, detail="Transaction already confirmed by sender")
        elif request.confirmation_type == "recipient" and transaction.get("recipient_confirmed_at"):
            raise HTTPException(status_code=400, detail="Transaction already confirmed by recipient")
        
        current_time = datetime.utcnow().isoformat()
        
        # Update confirmation based on type
        update_data = {}
        if request.confirmation_type == "sender":
            update_data["sender_confirmed_at"] = current_time
            if transaction.get("recipient_confirmed_at"):
                update_data["confirmation_status"] = ConfirmationStatus.BOTH_CONFIRMED
            else:
                update_data["confirmation_status"] = ConfirmationStatus.SENDER_CONFIRMED
        elif request.confirmation_type == "recipient":
            update_data["recipient_confirmed_at"] = current_time
            if transaction.get("sender_confirmed_at"):
                update_data["confirmation_status"] = ConfirmationStatus.BOTH_CONFIRMED
            else:
                update_data["confirmation_status"] = ConfirmationStatus.RECIPIENT_CONFIRMED
        
        # Update transaction
        update_result = db_manager.client.table("transaction").update(
            update_data
        ).eq("id", request.transaction_id).execute()
        
        if not update_result.data:
            raise HTTPException(status_code=500, detail="Failed to confirm transaction")
        
        updated_transaction = update_result.data[0]
        
        # If both parties have confirmed, trigger any completion logic
        if updated_transaction["confirmation_status"] == ConfirmationStatus.BOTH_CONFIRMED:
            await _handle_transaction_completion(updated_transaction)
        
        return {
            "message": "Transaction confirmed successfully",
            "confirmation_status": updated_transaction["confirmation_status"],
            "transaction_id": request.transaction_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def _handle_transaction_completion(transaction: dict):
    """Handle completion logic when both parties confirm a transaction."""
    try:
        # For contribution transactions, check if this completes a rotation
        if transaction["transaction_type"] == TransactionType.CONTRIBUTION:
            mypoolr_id = transaction["mypoolr_id"]
            to_member_id = transaction["to_member_id"]
            
            # Check if rotation is now complete
            is_complete = await RotationService.check_rotation_completion(mypoolr_id, to_member_id)
            
            if is_complete:
                # Advance to next rotation
                advancement_result = await RotationService.advance_rotation(mypoolr_id)
                
                if advancement_result.get("success"):
                    print(f"Rotation advanced for MyPoolr {mypoolr_id}: {advancement_result}")
                    # Here you could trigger notifications or other completion logic
                else:
                    print(f"Failed to advance rotation for MyPoolr {mypoolr_id}: {advancement_result.get('error')}")
                
    except Exception as e:
        # Log error but don't fail the confirmation
        print(f"Error in transaction completion handling: {str(e)}")


async def _check_rotation_completion(mypoolr_id: str, recipient_member_id: str):
    """Check if all contributions for current rotation are complete."""
    # This function is now handled by RotationService.check_rotation_completion
    return await RotationService.check_rotation_completion(mypoolr_id, recipient_member_id)


@router.get("/mypoolr/{mypoolr_id}", response_model=List[TransactionResponse])
async def get_mypoolr_transactions(mypoolr_id: UUID):
    """Get all transactions for a MyPoolr group."""
    try:
        result = db_manager.client.table("transaction").select("*").eq(
            "mypoolr_id", str(mypoolr_id)
        ).execute()
        
        return [TransactionResponse(**transaction) for transaction in result.data]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pending/{member_id}", response_model=List[TransactionResponse])
async def get_pending_confirmations(member_id: UUID):
    """Get all transactions pending confirmation by a specific member."""
    try:
        # Get transactions where member is sender and sender hasn't confirmed
        sender_pending = db_manager.client.table("transaction").select("*").eq(
            "from_member_id", str(member_id)
        ).is_("sender_confirmed_at", "null").execute()
        
        # Get transactions where member is recipient and recipient hasn't confirmed
        recipient_pending = db_manager.client.table("transaction").select("*").eq(
            "to_member_id", str(member_id)
        ).is_("recipient_confirmed_at", "null").execute()
        
        pending_transactions = []
        if sender_pending.data:
            pending_transactions.extend(sender_pending.data)
        if recipient_pending.data:
            pending_transactions.extend(recipient_pending.data)
        
        return [TransactionResponse(**transaction) for transaction in pending_transactions]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{transaction_id}/status")
async def get_transaction_status(transaction_id: UUID):
    """Get detailed status of a specific transaction."""
    try:
        result = db_manager.client.table("transaction").select("*").eq(
            "id", str(transaction_id)
        ).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        transaction = result.data[0]
        
        return {
            "transaction_id": str(transaction_id),
            "confirmation_status": transaction["confirmation_status"],
            "sender_confirmed": transaction.get("sender_confirmed_at") is not None,
            "recipient_confirmed": transaction.get("recipient_confirmed_at") is not None,
            "sender_confirmed_at": transaction.get("sender_confirmed_at"),
            "recipient_confirmed_at": transaction.get("recipient_confirmed_at"),
            "is_complete": transaction["confirmation_status"] == ConfirmationStatus.BOTH_CONFIRMED
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Rotation Management Endpoints

@router.get("/rotation/{mypoolr_id}/current")
async def get_current_rotation(mypoolr_id: UUID):
    """Get current rotation recipient for a MyPoolr."""
    try:
        current_recipient = await RotationService.get_current_rotation_recipient(str(mypoolr_id))
        
        if not current_recipient:
            raise HTTPException(status_code=404, detail="No current rotation recipient found")
        
        return current_recipient
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rotation/{mypoolr_id}/schedule")
async def get_rotation_schedule(mypoolr_id: UUID):
    """Get complete rotation schedule for a MyPoolr."""
    try:
        schedule = await RotationService.get_rotation_schedule(str(mypoolr_id))
        return {"mypoolr_id": str(mypoolr_id), "schedule": schedule}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rotation/{mypoolr_id}/advance")
async def advance_rotation(mypoolr_id: UUID):
    """Manually advance rotation to next member (admin only)."""
    try:
        # Validate that rotation can be advanced
        validation = await RotationService.validate_rotation_advancement(str(mypoolr_id))
        
        if not validation.get("can_advance"):
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot advance rotation: {validation.get('reason')}"
            )
        
        # Advance the rotation
        result = await RotationService.advance_rotation(str(mypoolr_id))
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to advance rotation: {result.get('error')}"
            )
        
        return {
            "message": "Rotation advanced successfully",
            "advancement_details": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rotation/{mypoolr_id}/validate")
async def validate_rotation_advancement(mypoolr_id: UUID):
    """Validate if rotation can be advanced."""
    try:
        validation = await RotationService.validate_rotation_advancement(str(mypoolr_id))
        return validation
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))