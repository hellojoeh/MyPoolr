"""Notification model definitions."""

from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID
from pydantic import Field
from .base import BaseModel


class NotificationType(str, Enum):
    """Notification type options."""
    ROTATION_START = "rotation_start"
    CONTRIBUTION_REMINDER = "contribution_reminder"
    CONTRIBUTION_CONFIRMED = "contribution_confirmed"
    ROTATION_COMPLETE = "rotation_complete"
    DEFAULT_WARNING = "default_warning"
    DEFAULT_HANDLED = "default_handled"
    SECURITY_DEPOSIT_REQUIRED = "security_deposit_required"
    SECURITY_DEPOSIT_RETURNED = "security_deposit_returned"
    MEMBER_JOINED = "member_joined"
    MEMBER_LEFT = "member_left"
    TIER_UPGRADED = "tier_upgraded"
    TIER_DOWNGRADED = "tier_downgraded"
    SYSTEM_ALERT = "system_alert"


class NotificationPriority(str, Enum):
    """Notification priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationStatus(str, Enum):
    """Notification delivery status."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRY = "retry"


class NotificationChannel(str, Enum):
    """Notification delivery channels."""
    TELEGRAM = "telegram"
    SMS = "sms"
    EMAIL = "email"
    PUSH = "push"


class Notification(BaseModel):
    """Notification model for all system notifications."""
    
    mypoolr_id: Optional[UUID] = Field(None, description="Reference to MyPoolr group")
    recipient_id: int = Field(..., description="Telegram user ID of recipient")
    notification_type: NotificationType
    priority: NotificationPriority = Field(default=NotificationPriority.NORMAL)
    channel: NotificationChannel = Field(default=NotificationChannel.TELEGRAM)
    
    title: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1, max_length=2000)
    
    status: NotificationStatus = Field(default=NotificationStatus.PENDING)
    scheduled_at: Optional[datetime] = Field(None, description="When to send notification")
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    
    retry_count: int = Field(default=0, ge=0, le=5)
    max_retries: int = Field(default=3, ge=0, le=10)
    
    metadata: Dict[str, Any] = Field(default_factory=dict)
    template_data: Dict[str, Any] = Field(default_factory=dict)
    
    # Localization support
    language_code: str = Field(default="en", min_length=2, max_length=5)
    country_code: str = Field(default="US", min_length=2, max_length=2)


class NotificationTemplate(BaseModel):
    """Notification template for localization support."""
    
    template_key: str = Field(..., min_length=1, max_length=100)
    notification_type: NotificationType
    language_code: str = Field(..., min_length=2, max_length=5)
    country_code: str = Field(..., min_length=2, max_length=2)
    
    title_template: str = Field(..., min_length=1, max_length=200)
    message_template: str = Field(..., min_length=1, max_length=2000)
    
    variables: Dict[str, str] = Field(default_factory=dict, description="Template variable descriptions")
    is_active: bool = Field(default=True)