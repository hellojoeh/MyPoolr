"""Member model definitions."""

from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID
from pydantic import Field
from .base import BaseModel


class MemberStatus(str, Enum):
    """Member status options."""
    ACTIVE = "active"
    PENDING = "pending"
    SUSPENDED = "suspended"
    REMOVED = "removed"


class SecurityDepositStatus(str, Enum):
    """Security deposit status options."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    LOCKED = "locked"
    RETURNED = "returned"
    USED = "used"


class Member(BaseModel):
    """Member model for MyPoolr participants."""
    
    mypoolr_id: UUID = Field(..., description="Reference to MyPoolr group")
    telegram_id: int = Field(..., description="Telegram user ID")
    name: str = Field(..., min_length=1, max_length=100)
    phone_number: str = Field(..., min_length=10, max_length=15)
    rotation_position: int = Field(..., ge=1)
    security_deposit_amount: Decimal = Field(..., ge=0)
    security_deposit_status: SecurityDepositStatus = Field(default=SecurityDepositStatus.PENDING)
    has_received_payout: bool = Field(default=False)
    is_locked_in: bool = Field(default=False, description="Prevents leaving after payout")
    status: MemberStatus = Field(default=MemberStatus.PENDING)