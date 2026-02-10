"""Tier management service for MyPoolr groups."""

from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

from models.mypoolr import TierLevel
from database import DatabaseManager


class TierFeatures(BaseModel):
    """Features available for each tier."""
    
    max_groups: int = Field(..., description="Maximum number of groups admin can create")
    max_members_per_group: int = Field(..., description="Maximum members per group")
    reminder_frequency_hours: int = Field(..., description="Hours between reminders")
    priority_support: bool = Field(default=False, description="Access to priority support")
    advanced_analytics: bool = Field(default=False, description="Access to advanced analytics")
    custom_rotation_schedules: bool = Field(default=False, description="Custom rotation scheduling")
    bulk_member_management: bool = Field(default=False, description="Bulk member operations")
    export_data: bool = Field(default=False, description="Data export capabilities")


class TierPricing(BaseModel):
    """Pricing information for each tier."""
    
    monthly_price: Decimal = Field(..., description="Monthly subscription price")
    currency: str = Field(default="KES", description="Currency code")
    trial_days: int = Field(default=0, description="Free trial period in days")


class TierConfiguration:
    """Configuration for all tier levels."""
    
    TIER_CONFIGS: Dict[TierLevel, Dict] = {
        TierLevel.STARTER: {
            "features": TierFeatures(
                max_groups=1,
                max_members_per_group=10,
                reminder_frequency_hours=24,
                priority_support=False,
                advanced_analytics=False,
                custom_rotation_schedules=False,
                bulk_member_management=False,
                export_data=False
            ),
            "pricing": TierPricing(
                monthly_price=Decimal("0.00"),
                currency="KES",
                trial_days=0
            ),
            "name": "Starter",
            "description": "Perfect for small groups getting started"
        },
        TierLevel.ESSENTIAL: {
            "features": TierFeatures(
                max_groups=3,
                max_members_per_group=25,
                reminder_frequency_hours=12,
                priority_support=False,
                advanced_analytics=True,
                custom_rotation_schedules=False,
                bulk_member_management=False,
                export_data=True
            ),
            "pricing": TierPricing(
                monthly_price=Decimal("500.00"),
                currency="KES",
                trial_days=7
            ),
            "name": "Essential",
            "description": "Great for growing communities with analytics"
        },
        TierLevel.ADVANCED: {
            "features": TierFeatures(
                max_groups=10,
                max_members_per_group=50,
                reminder_frequency_hours=6,
                priority_support=True,
                advanced_analytics=True,
                custom_rotation_schedules=True,
                bulk_member_management=True,
                export_data=True
            ),
            "pricing": TierPricing(
                monthly_price=Decimal("1500.00"),
                currency="KES",
                trial_days=14
            ),
            "name": "Advanced",
            "description": "Full-featured for serious group managers"
        },
        TierLevel.EXTENDED: {
            "features": TierFeatures(
                max_groups=50,
                max_members_per_group=100,
                reminder_frequency_hours=2,
                priority_support=True,
                advanced_analytics=True,
                custom_rotation_schedules=True,
                bulk_member_management=True,
                export_data=True
            ),
            "pricing": TierPricing(
                monthly_price=Decimal("3000.00"),
                currency="KES",
                trial_days=30
            ),
            "name": "Extended",
            "description": "Enterprise-level for large organizations"
        }
    }


class TierSubscription(BaseModel):
    """Tier subscription model."""
    
    admin_id: int = Field(..., description="Telegram user ID of admin")
    tier: TierLevel = Field(..., description="Current tier level")
    subscription_start: datetime = Field(..., description="Subscription start date")
    subscription_end: Optional[datetime] = Field(None, description="Subscription end date")
    is_active: bool = Field(default=True, description="Whether subscription is active")
    payment_reference: Optional[str] = Field(None, description="Payment reference ID")
    auto_renew: bool = Field(default=True, description="Whether to auto-renew subscription")


class TierUpgradeRequest(BaseModel):
    """Request model for tier upgrades."""
    
    admin_id: int = Field(..., description="Telegram user ID of admin")
    target_tier: TierLevel = Field(..., description="Desired tier level")
    payment_method: str = Field(default="mpesa", description="Payment method")
    phone_number: Optional[str] = Field(None, description="Phone number for payment")


class TierValidationError(Exception):
    """Exception raised when tier validation fails."""
    pass


class TierManagementService:
    """Service for managing tier subscriptions and feature access."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.config = TierConfiguration()
    
    def get_tier_features(self, tier: TierLevel) -> TierFeatures:
        """Get features for a specific tier."""
        return self.config.TIER_CONFIGS[tier]["features"]
    
    def get_tier_pricing(self, tier: TierLevel) -> TierPricing:
        """Get pricing for a specific tier."""
        return self.config.TIER_CONFIGS[tier]["pricing"]
    
    def get_tier_info(self, tier: TierLevel) -> Dict:
        """Get complete tier information."""
        return self.config.TIER_CONFIGS[tier]
    
    def get_all_tiers(self) -> Dict[TierLevel, Dict]:
        """Get information for all available tiers."""
        return self.config.TIER_CONFIGS
    
    async def get_admin_tier(self, admin_id: int) -> TierLevel:
        """Get current tier for an admin."""
        try:
            result = self.db.client.table("tier_subscriptions").select("*").eq("admin_id", admin_id).eq("is_active", True).single().execute()
            
            if result.data:
                return TierLevel(result.data["tier"])
            else:
                # Default to starter tier if no subscription found
                return TierLevel.STARTER
        except Exception:
            # Default to starter tier on error
            return TierLevel.STARTER
    
    async def validate_tier_limits(self, admin_id: int, action: str, **kwargs) -> bool:
        """Validate if admin can perform action based on tier limits."""
        current_tier = await self.get_admin_tier(admin_id)
        features = self.get_tier_features(current_tier)
        
        if action == "create_group":
            # Check if admin can create another group
            current_groups = await self._count_admin_groups(admin_id)
            return current_groups < features.max_groups
        
        elif action == "add_member":
            # Check if group can accept another member
            group_id = kwargs.get("group_id")
            if not group_id:
                return False
            
            current_members = await self._count_group_members(group_id)
            return current_members < features.max_members_per_group
        
        elif action == "access_analytics":
            return features.advanced_analytics
        
        elif action == "export_data":
            return features.export_data
        
        elif action == "bulk_operations":
            return features.bulk_member_management
        
        elif action == "custom_schedules":
            return features.custom_rotation_schedules
        
        return True
    
    async def create_tier_upgrade_request(self, request: TierUpgradeRequest) -> Dict:
        """Create a tier upgrade request."""
        current_tier = await self.get_admin_tier(request.admin_id)
        
        # Validate upgrade path
        if not self._is_valid_upgrade(current_tier, request.target_tier):
            raise TierValidationError(f"Invalid upgrade from {current_tier} to {request.target_tier}")
        
        # Calculate pricing
        target_pricing = self.get_tier_pricing(request.target_tier)
        
        # Create upgrade request record
        upgrade_data = {
            "admin_id": request.admin_id,
            "current_tier": current_tier.value,
            "target_tier": request.target_tier.value,
            "amount": float(target_pricing.monthly_price),
            "currency": target_pricing.currency,
            "payment_method": request.payment_method,
            "phone_number": request.phone_number,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat()
        }
        
        result = await self.db.client.table("tier_upgrade_requests").insert(upgrade_data).execute()
        
        return {
            "upgrade_request_id": result.data[0]["id"],
            "amount": target_pricing.monthly_price,
            "currency": target_pricing.currency,
            "target_tier": request.target_tier,
            "features": self.get_tier_features(request.target_tier)
        }
    
    async def process_tier_upgrade(self, admin_id: int, target_tier: TierLevel, payment_reference: str) -> bool:
        """Process successful tier upgrade."""
        try:
            # Calculate subscription period
            subscription_start = datetime.utcnow()
            subscription_end = subscription_start + timedelta(days=30)  # Monthly subscription
            
            # Deactivate current subscription
            await self.db.client.table("tier_subscriptions").update({
                "is_active": False,
                "updated_at": subscription_start.isoformat()
            }).eq("admin_id", admin_id).eq("is_active", True).execute()
            
            # Create new subscription
            subscription_data = {
                "admin_id": admin_id,
                "tier": target_tier.value,
                "subscription_start": subscription_start.isoformat(),
                "subscription_end": subscription_end.isoformat(),
                "is_active": True,
                "payment_reference": payment_reference,
                "auto_renew": True,
                "created_at": subscription_start.isoformat()
            }
            
            await self.db.client.table("tier_subscriptions").insert(subscription_data).execute()
            
            # Update upgrade request status
            await self.db.client.table("tier_upgrade_requests").update({
                "status": "completed",
                "payment_reference": payment_reference,
                "completed_at": subscription_start.isoformat()
            }).eq("admin_id", admin_id).eq("target_tier", target_tier.value).eq("status", "pending").execute()
            
            return True
            
        except Exception as e:
            print(f"Error processing tier upgrade: {e}")
            return False
    
    async def handle_tier_downgrade(self, admin_id: int) -> TierLevel:
        """Handle tier downgrade when subscription expires."""
        try:
            # Deactivate expired subscription
            await self.db.client.table("tier_subscriptions").update({
                "is_active": False,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("admin_id", admin_id).eq("is_active", True).execute()
            
            # Check if admin has any paid subscription history
            result = await self.db.client.table("tier_subscriptions").select("tier").eq("admin_id", admin_id).order("created_at", desc=True).limit(1).execute()
            
            if result.data and result.data[0]["tier"] != TierLevel.STARTER.value:
                # Downgrade to Essential if they had a paid tier
                downgrade_tier = TierLevel.ESSENTIAL
            else:
                # Downgrade to Starter for first-time users
                downgrade_tier = TierLevel.STARTER
            
            # Create new subscription at downgraded tier
            subscription_data = {
                "admin_id": admin_id,
                "tier": downgrade_tier.value,
                "subscription_start": datetime.utcnow().isoformat(),
                "subscription_end": None,  # Free tier has no expiration
                "is_active": True,
                "payment_reference": None,
                "auto_renew": False,
                "created_at": datetime.utcnow().isoformat()
            }
            
            await self.db.client.table("tier_subscriptions").insert(subscription_data).execute()
            
            return downgrade_tier
            
        except Exception as e:
            print(f"Error handling tier downgrade: {e}")
            return TierLevel.STARTER
    
    async def check_subscription_expiry(self, admin_id: int) -> bool:
        """Check if admin's subscription has expired."""
        try:
            result = await self.db.client.table("tier_subscriptions").select("*").eq("admin_id", admin_id).eq("is_active", True).single().execute()
            
            if not result.data:
                return True  # No active subscription
            
            subscription = result.data
            if subscription["subscription_end"]:
                expiry_date = datetime.fromisoformat(subscription["subscription_end"])
                return datetime.utcnow() > expiry_date
            
            return False  # No expiry date (free tier)
            
        except Exception:
            return True  # Assume expired on error
    
    def _is_valid_upgrade(self, current_tier: TierLevel, target_tier: TierLevel) -> bool:
        """Check if upgrade path is valid."""
        tier_order = [TierLevel.STARTER, TierLevel.ESSENTIAL, TierLevel.ADVANCED, TierLevel.EXTENDED]
        current_index = tier_order.index(current_tier)
        target_index = tier_order.index(target_tier)
        
        # Allow upgrades to higher tiers only
        return target_index > current_index
    
    async def _count_admin_groups(self, admin_id: int) -> int:
        """Count number of groups created by admin."""
        try:
            result = self.db.client.table("mypoolr").select("id", count="exact").eq("admin_id", admin_id).eq("status", "active").execute()
            return result.count or 0
        except Exception:
            return 0
    
    async def _count_group_members(self, group_id: UUID) -> int:
        """Count number of members in a group."""
        try:
            result = self.db.client.table("member").select("id", count="exact").eq("mypoolr_id", str(group_id)).eq("status", "active").execute()
            return result.count or 0
        except Exception:
            return 0