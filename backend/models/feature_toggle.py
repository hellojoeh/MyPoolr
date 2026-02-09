"""Feature toggle models for dynamic feature management."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, Dict, Any, List
from uuid import UUID

from .base import BaseModel


class FeatureScope(str, Enum):
    """Scope levels for feature toggles."""
    GLOBAL = "global"
    COUNTRY = "country"
    GROUP = "group"
    USER = "user"


class ToggleStatus(str, Enum):
    """Status of a feature toggle."""
    ENABLED = "enabled"
    DISABLED = "disabled"
    TESTING = "testing"


class FeatureDefinition(BaseModel):
    """Definition of a feature that can be toggled."""
    
    id: UUID
    name: str
    description: str
    category: str
    default_enabled: bool = False
    requires_tier: Optional[str] = None
    regulatory_restricted: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None


class CountryConfig(BaseModel):
    """Country-specific configuration and restrictions."""
    
    id: UUID
    country_code: str
    country_name: str
    currency_code: str
    timezone: str
    locale: str = "en_US"
    payment_providers: List[str] = []
    regulatory_restrictions: Dict[str, Any] = {}
    is_active: bool = True
    created_at: datetime
    updated_at: Optional[datetime] = None


class FeatureToggle(BaseModel):
    """Dynamic feature toggle configuration."""
    
    id: UUID
    feature_name: str
    scope: FeatureScope
    scope_value: Optional[str] = None
    status: ToggleStatus = ToggleStatus.ENABLED
    percentage_rollout: Optional[int] = None
    conditions: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}
    expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class FeatureUsage(BaseModel):
    """Tracking of feature usage for analytics."""
    
    id: UUID
    feature_name: str
    user_id: int  # Telegram user ID
    mypoolr_id: Optional[UUID] = None
    country_code: Optional[str] = None
    usage_count: int = 1
    first_used_at: datetime
    last_used_at: datetime


class FeatureContext:
    """Context for feature toggle evaluation."""
    
    def __init__(
        self,
        user_id: Optional[int] = None,
        mypoolr_id: Optional[UUID] = None,
        country_code: Optional[str] = None,
        tier: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.user_id = user_id
        self.mypoolr_id = mypoolr_id
        self.country_code = country_code
        self.tier = tier
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary for logging/debugging."""
        return {
            "user_id": self.user_id,
            "mypoolr_id": str(self.mypoolr_id) if self.mypoolr_id else None,
            "country_code": self.country_code,
            "tier": self.tier,
            "metadata": self.metadata
        }