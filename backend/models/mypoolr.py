"""MyPoolr model definitions."""

from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID
from pydantic import Field
from .base import BaseModel


class RotationFrequency(str, Enum):
    """Rotation frequency options."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class TierLevel(str, Enum):
    """Tier levels for MyPoolr groups."""
    STARTER = "starter"
    ESSENTIAL = "essential"
    ADVANCED = "advanced"
    EXTENDED = "extended"


class MyPoolrStatus(str, Enum):
    """MyPoolr status options."""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class MyPoolr(BaseModel):
    """MyPoolr savings group model."""
    
    name: str = Field(..., min_length=1, max_length=100)
    admin_id: int = Field(..., description="Telegram user ID of admin")
    contribution_amount: Decimal = Field(..., gt=0)
    rotation_frequency: RotationFrequency
    member_limit: int = Field(..., ge=2, le=100)
    tier: TierLevel = Field(default=TierLevel.STARTER)
    security_deposit_multiplier: float = Field(default=1.0, ge=0.5, le=3.0)
    status: MyPoolrStatus = Field(default=MyPoolrStatus.ACTIVE)
    current_rotation_position: int = Field(default=0, description="Current position in rotation cycle")
    total_rotations_completed: int = Field(default=0, description="Number of complete rotation cycles")