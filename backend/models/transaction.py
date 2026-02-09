"""Transaction model definitions."""

from decimal import Decimal
from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID
from pydantic import Field
from .base import BaseModel


class TransactionType(str, Enum):
    """Transaction type options."""
    CONTRIBUTION = "contribution"
    SECURITY_DEPOSIT = "security_deposit"
    TIER_UPGRADE = "tier_upgrade"
    DEPOSIT_RETURN = "deposit_return"
    DEFAULT_COVERAGE = "default_coverage"


class ConfirmationStatus(str, Enum):
    """Confirmation status for transactions."""
    PENDING = "pending"
    SENDER_CONFIRMED = "sender_confirmed"
    RECIPIENT_CONFIRMED = "recipient_confirmed"
    BOTH_CONFIRMED = "both_confirmed"
    CANCELLED = "cancelled"


class Transaction(BaseModel):
    """Transaction model for all financial activities."""
    
    mypoolr_id: UUID = Field(..., description="Reference to MyPoolr group")
    from_member_id: Optional[UUID] = Field(None, description="Sender member ID")
    to_member_id: Optional[UUID] = Field(None, description="Recipient member ID")
    amount: Decimal = Field(..., gt=0)
    transaction_type: TransactionType
    confirmation_status: ConfirmationStatus = Field(default=ConfirmationStatus.PENDING)
    sender_confirmed_at: Optional[datetime] = None
    recipient_confirmed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    notes: Optional[str] = Field(None, max_length=500)